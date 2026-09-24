from __future__ import annotations

from google.genai import types

from .config import get_settings
from .gemini_generator import get_gemini_client
from .schemas import NutritionTip, UserInput


def _mock_tip(
    user: UserInput,
) -> NutritionTip:

    tips = {

        "muscle_gain":
            "Include a protein-rich food in each "
            "main meal and eat a balanced meal "
            "after training.",

        "weight_loss":
            "Build meals around vegetables, "
            "a protein source, whole-food "
            "carbohydrates, and reasonable portions.",

        "flexibility":
            "Stay hydrated and pair mobility "
            "work with balanced meals that include "
            "protein and produce.",

        "general_wellness":
            "Prioritize regular balanced meals, "
            "hydration, vegetables, whole-food "
            "carbohydrates, and adequate protein.",
    }

    return NutritionTip(
        tip=tips[user.goal],

        recovery_note=(
            "Aim for consistent sleep and include "
            "easier recovery periods between "
            "demanding sessions."
        ),
    )


def generate_nutrition_tip_with_flash(
    user: UserInput,
) -> NutritionTip:

    settings = get_settings()

    if settings.mock_ai:
        return _mock_tip(user)

    client = get_gemini_client()

    prompt = f"""
Generate one concise nutrition/recovery
recommendation for a fitness app.

Goal: {user.goal}

Intensity: {user.intensity}

Age: {user.age}

Weight: {user.weight_kg} kg

Keep it practical and general.

Do not calculate medical diets.

Do not diagnose medical conditions.

Do not prescribe supplements.

Do not prescribe medication.

Return one tip and one recovery note.
"""

    response = client.models.generate_content(
        model=settings.gemini_fast_model,

        contents=prompt,

        config=types.GenerateContentConfig(
            response_mime_type="application/json",

            response_schema=NutritionTip,

            temperature=0.3,

            max_output_tokens=800,
        ),
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty nutrition tip."
        )

    return NutritionTip.model_validate_json(
        response.text
    )