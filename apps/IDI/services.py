import os, re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class KeyInteractionSchema(BaseModel):
    interaction_title: str = Field(
        description="Name of interacting drug or factor"
    )
    clinical_impact: str = Field(
        description="Clinical consequence of the interaction"
    )
    what_to_do: str = Field(
        description="Recommended action for prescriber"
    )

class PracticalPearlSchema(BaseModel):
    pearl_title: str = Field(
        description="Short title summarizing the prescribing pearl"
    )
    pearl_content: str = Field(
        description="Concise practical prescribing advice"
    )

class IDIExtractionSchema(BaseModel):
    # Basic Drug Information
    drug_name_generic: Optional[str]
    drug_class: Optional[str]
    therapeutic_category: Optional[str]
    brands_in_india: Optional[str]
    strengths_available: Optional[str]
    formulations_routes: Optional[str]

    # Clinical Information
    core_clinical_role: Optional[str]
    preferred_clinical_scenarios: Optional[str]
    where_benefit_limited: Optional[str]

    # Dosing Information
    usual_adult_dose: Optional[str]
    timing_relative_to_meals: Optional[str]
    review_duration_plan: Optional[str]

    # Safety Information
    common_adverse_effects: Optional[str]
    serious_but_uncommon_risks: Optional[str]
    long_term_therapy_cautions: Optional[str]

    # Evidence Base
    guidelines: Optional[str] = None
    landmark_trials: Optional[str] = None

    # Nested Structured Fields
    key_interactions: List[KeyInteractionSchema] = []
    practical_prescribing_pearls: List[PracticalPearlSchema] = []

    # Metadata
    status: str = Field(default="draft")


IDI_EXTRACTION_PROMPT_BODY = """
You are a clinical pharmacology data extraction engine.
Your task is to extract structured drug information from a free-text paragraph and return STRICT JSON that conforms EXACTLY to the provided schema.

Rules:

1. Output ONLY valid JSON.
2. Do NOT include explanations.
3. Do NOT include markdown.
4. Do NOT add extra fields.
5. If a field is not mentioned, return null.
6. If a list field has no data, return an empty array [].
7. Be precise. Do not infer facts not explicitly stated.
8. Preserve medical accuracy.
9. Do not hallucinate guideline or trial names.
10. All string values must be concise and clinically relevant.

The JSON must match the schema exactly.

Extract structured drug information from the paragraph below.

Paragraph:
{paragraph}


Return JSON with the following fields:

- drug_name_generic (string)
- drug_class (string)
- therapeutic_category (string)
- brands_in_india (string)
- strengths_available (string)
- formulations_routes (string)
- core_clinical_role (string)
- preferred_clinical_scenarios (string)
- where_benefit_limited (string)
- usual_adult_dose (string)
- timing_relative_to_meals (string)
- review_duration_plan (string)
- common_adverse_effects (string)
- serious_but_uncommon_risks (string)
- long_term_therapy_cautions (string)
- guidelines (string or null)
- landmark_trials (string or null)
- key_interactions (array of objects)
    - interaction_title (string)
    - clinical_impact (string)
    - what_to_do (string)
- practical_prescribing_pearls (array of objects)
    - pearl_title (string)
    - pearl_content (string)
- status (string; always return "draft")
"""
IDI_EXTRACTION_PROMPT = PromptTemplate(
    input_variables=["paragraph"],
    template=IDI_EXTRACTION_PROMPT_BODY,
)





class IDIExtractionService:
    WORD_HEADER_MAP = {
        "DRUG NAME (GENERIC)": "drug_name_generic",
        "DRUG CLASS": "drug_class",
        "THERAPEUTIC CATEGORY": "therapeutic_category",
        "BRANDS IN INDIA – SINGLE MOLECULE": "brands_in_india",
        "BRANDS IN INDIA - SINGLE MOLECULE": "brands_in_india",
        "STRENGTHS AVAILABLE": "strengths_available",
        "FORMULATIONS / ROUTES": "formulations_routes",
        "CORE CLINICAL ROLE": "core_clinical_role",
        "PREFERRED CLINICAL SCENARIOS": "preferred_clinical_scenarios",
        "WHERE BENEFIT IS LIMITED / AVOID OVERUSE": "where_benefit_limited",
        "USUAL ADULT DOSE": "usual_adult_dose",
        "TIMING RELATIVE TO MEALS": "timing_relative_to_meals",
        "REVIEW / DURATION PLAN": "review_duration_plan",
        "COMMON ADVERSE EFFECTS": "common_adverse_effects",
        "SERIOUS BUT UNCOMMON RISKS": "serious_but_uncommon_risks",
        "LONG-TERM THERAPY CAUTIONS": "long_term_therapy_cautions",
        "GUIDELINES (NAME + YEAR)": "guidelines",
        "LANDMARK TRIALS (NAME + YEAR)": "landmark_trials",
    }

    SPECIAL_HEADERS = {
        "KEY INTERACTIONS": "interactions",
        "PRACTICAL PRESCRIBING PEARLS": "pearls",
    }

    @staticmethod
    def ai_extract(paragraph: str) -> dict:
        openai_llm = ChatOpenAI(
            model="gpt-4.1-mini-2025-04-14",
            api_key=os.environ.get("OPENAI_API_KEY"),  
            temperature=0, max_tokens=2048,
            max_retries=2, timeout=600
        )
        structure_llm = openai_llm.with_structured_output(IDIExtractionSchema)
        prompt = IDI_EXTRACTION_PROMPT.format(paragraph=paragraph)
        response = structure_llm.invoke(prompt)
        return response.model_dump()

    # ---------------------------------
    # Public entry point
    # ---------------------------------
    def extract(self, raw_text: str) -> Dict:
        normalized = raw_text.replace("\r\n", "\n")
        lines = normalized.split("\n")
        parsed = self._parse_sections(lines)
        structured = self._build_model(parsed)
        return structured

    # ---------------------------------
    # Core section parser
    # ---------------------------------
    def _parse_sections(self, lines: List[str]) -> Dict:
        allowed_headers = set(
            [self._norm(h) for h in self.WORD_HEADER_MAP.keys()] +
            [self._norm(h) for h in self.SPECIAL_HEADERS.keys()]
        )

        current_header = None
        buffer = []

        result = {
            "simple": {},
            "interactions_raw": [],
            "pearls_raw": [],
        }

        def flush():
            nonlocal buffer, current_header
            if not current_header:
                return

            content = "\n".join(buffer).strip()
            if not content:
                buffer = []
                return

            if current_header == self._norm("KEY INTERACTIONS"):
                result["interactions_raw"].append(content)
            elif current_header == self._norm("PRACTICAL PRESCRIBING PEARLS"):
                result["pearls_raw"].append(content)
            else:
                result["simple"].setdefault(current_header, "")
                if result["simple"][current_header]:
                    result["simple"][current_header] += "\n" + content
                else:
                    result["simple"][current_header] = content

            buffer = []

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                if buffer:
                    buffer.append("")
                continue

            normalized = self._norm(line)

            if normalized in allowed_headers:
                flush()
                current_header = normalized
                continue

            buffer.append(raw_line)

        flush()

        result["interactions"] = self._parse_interactions(
            "\n".join(result["interactions_raw"])
        )
        result["pearls"] = self._parse_pearls(
            "\n".join(result["pearls_raw"])
        )

        return result

    # ---------------------------------
    # Build final structured model
    # ---------------------------------
    def _build_model(self, parsed: Dict) -> Dict:
        model = {
            "drug_name_generic": "",
            "drug_class": "",
            "therapeutic_category": "",
            "brands_in_india": "",
            "strengths_available": "",
            "formulations_routes": "",
            "core_clinical_role": "",
            "preferred_clinical_scenarios": "",
            "where_benefit_limited": "",
            "usual_adult_dose": "",
            "timing_relative_to_meals": "",
            "review_duration_plan": "",
            "common_adverse_effects": "",
            "serious_but_uncommon_risks": "",
            "long_term_therapy_cautions": "",
            "guidelines": "",
            "landmark_trials": "",
            "key_interactions": [],
            "practical_prescribing_pearls": [],
        }

        for header, content in parsed["simple"].items():
            field_key = self.WORD_HEADER_MAP.get(header)
            if field_key:
                model[field_key] = content.strip()

        model["key_interactions"] = [
            {
                "interaction_title": item.get("interaction_title", ""),
                "clinical_impact": item.get("clinical_impact", ""),
                "what_to_do": item.get("what_to_do", ""),
            }
            for item in parsed["interactions"]
        ]


        model["practical_prescribing_pearls"] = [
            {
                "pearl_title": item.get("pearl_title", ""),
                "pearl_content": item.get("pearl_content", ""),
            }
            for item in parsed["pearls"]
        ]


        return model

    # ---------------------------------
    # Repeatable blocks
    # ---------------------------------
    def _parse_interactions(self, raw: str) -> List[Dict]:
        lines = raw.split("\n")

        items = []
        current = {"interaction_title": "", "clinical_impact": "", "what_to_do": ""}
        mode = None

        for line in lines:
            stripped = line.strip()
            upper = stripped.upper()

            if upper.startswith(">> INTERACTION TITLE"):
                if any(current.values()):
                    items.append(current)
                    current = {"interaction_title": "", "clinical_impact": "", "what_to_do": ""}
                mode = "interaction_title"
                continue

            if upper.startswith(">> CLINICAL IMPACT"):
                mode = "clinical_impact"
                continue

            if upper.startswith(">> WHAT TO DO"):
                mode = "what_to_do"
                continue

            if mode:
                if current[mode]:
                    current[mode] += "\n" + line
                else:
                    current[mode] = line

        if any(current.values()):
            items.append(current)

        return items

    def _parse_pearls(self, raw: str) -> List[Dict]:
        lines = raw.split("\n")

        items = []
        current = {"pearl_title": "", "pearl_content": ""}
        mode = None

        for line in lines:
            stripped = line.strip()
            upper = stripped.upper()

            if upper.startswith(">> PEARL TITLE"):
                if any(current.values()):
                    items.append(current)
                    current = {"pearl_title": "", "pearl_content": ""}
                mode = "pearl_title"
                continue

            if upper.startswith(">> PEARL CONTENT"):
                mode = "pearl_content"
                continue

            if mode:
                if current[mode]:
                    current[mode] += "\n" + line
                else:
                    current[mode] = line

        if any(current.values()):
            items.append(current)

        return items

    # ---------------------------------
    # Utilities
    # ---------------------------------
    def _norm(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().upper())
