from __future__ import annotations

from google import genai
from google.genai import types

from .config import get_settings
from .gemini_generator import _mock_plan
from .schemas import UserInput, WorkoutPlan


def update_workout_plan(user: UserInput, original_plan: str, feedback: str) -> WorkoutPlan:
    settings = get_settings()

    if settings.mock_ai:
        revised = _mock_plan(user)
        revised.title += " — Revised"
        revised.summary += f" Feedback applied: {feedback}"
        return revised

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured. Add it to .env or enable MOCK_AI=true.")

    prompt = f"""
You are revising an existing FitBuddy 7-day workout plan.

User profile:
- Name: {user.name}
- Age: {user.age}
- Weight: {user.weight_kg} kg
- Goal: {user.goal}
- Intensity: {user.intensity}

Original plan:
{original_plan}

User feedback:
{feedback}

Create a revised 7-day plan that incorporates the feedback where it is safe and
reasonable. Preserve the user's goal and selected intensity unless the feedback
clearly asks for a safe adjustment. Return exactly 7 days with the same structured
fields. Do not diagnose conditions or prescribe medication.
"""

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_workout_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=WorkoutPlan,
            temperature=0.4,
            max_output_tokens=7000,
        ),
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty revised plan.")
    return WorkoutPlan.model_validate_json(response.text)
