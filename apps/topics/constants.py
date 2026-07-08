from django.db import models


class Mood(models.TextChoices):
    """Writing-style / tone options that can be injected into any AI prompt.

    The stored value doubles as the label the admin UI shows, so the frontend
    dropdown and the backend validation stay in sync with a single source of
    truth. ``NEUTRAL`` means "use the existing/default writing style" and
    produces no extra prompt instructions.
    """

    NEUTRAL = "Neutral", "Neutral"
    PROFESSIONAL = "Professional", "Professional"
    PROMOTIONAL = "Promotional", "Promotional"
    SIMPLIFIED = "Simplified", "Simplified"
    PATIENT_FRIENDLY = "Patient-Friendly", "Patient-Friendly"
    ACADEMIC = "Academic / Physician-Facing", "Academic / Physician-Facing"
    CONVERSATIONAL = "Conversational", "Conversational"
    CREATIVE = "Creative", "Creative"
    SERIOUS = "Serious", "Serious"
    EMPATHETIC = "Empathetic", "Empathetic"


DEFAULT_MOOD = Mood.NEUTRAL


# Mood -> tone instruction. Neutral is intentionally absent (empty instruction)
# so the base prompt keeps its default style untouched.
MOOD_INSTRUCTIONS = {
    Mood.PROFESSIONAL: "use a formal, authoritative, and business-like tone",
    Mood.PROMOTIONAL: (
        "use persuasive, engaging, marketing-oriented language while remaining "
        "factually accurate"
    ),
    Mood.SIMPLIFIED: "explain concepts in plain, simple language for a general audience",
    Mood.PATIENT_FRIENDLY: (
        "use simple, reassuring, and easy-to-understand language suitable for patients"
    ),
    Mood.ACADEMIC: (
        "use clinical terminology and a professional medical writing style suitable "
        "for physicians"
    ),
    Mood.CONVERSATIONAL: "write in a friendly, natural, and conversational tone",
    Mood.CREATIVE: "use engaging and imaginative language where appropriate",
    Mood.SERIOUS: "maintain a formal, serious, and objective tone",
    Mood.EMPATHETIC: "use compassionate, supportive, and empathetic language",
}


def build_mood_instruction(mood) -> str:
    """Return a tone/style block for ``mood`` that can be injected into any AI prompt.

    Returns an empty string for Neutral, an unknown value, or a missing value so
    the base prompt is used unchanged. Lookup tolerates casing/whitespace
    variations in the incoming value.
    """
    if not mood:
        return ""

    instruction = MOOD_INSTRUCTIONS.get(mood)
    if instruction is None:
        normalized = str(mood).strip().lower()
        for key, value in MOOD_INSTRUCTIONS.items():
            if str(key).lower() == normalized:
                instruction = value
                break

    if not instruction:
        return ""

    return (
        "\nTone & Writing Style:\n"
        f"- Write in the following style: {instruction}.\n"
        "- Keep the original meaning and factual accuracy intact; only adapt the tone.\n"
    )
