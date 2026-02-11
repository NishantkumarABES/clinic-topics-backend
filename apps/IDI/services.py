import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from typing import List, Optional
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

    @staticmethod
    def extract(paragraph: str) -> dict:
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



