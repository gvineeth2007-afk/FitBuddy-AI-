from __future__ import annotations

import time

from google import genai
from google.genai import types

from .config import get_settings
from .schemas import UserInput, WorkoutPlan


_gemini_client: genai.Client | None = None


def get_gemini_client() -> genai.Client:

    global _gemini_client

    settings = get_settings()

    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Add it to .env or set MOCK_AI=true."
        )

    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=settings.gemini_api_key
        )

    return _gemini_client


def close_gemini_client() -> None:

    global _gemini_client

    if _gemini_client is not None:

        try:
            _gemini_client.close()

        finally:
            _gemini_client = None


def _mock_plan(
    user: UserInput,
) -> WorkoutPlan:

    focuses = [
        "Full body strength",
        "Cardio + core",
        "Lower body",
        "Active recovery",
        "Upper body",
        "Conditioning",
        "Mobility + recovery",
    ]

    days = []

    for i, focus in enumerate(focuses, start=1):

        days.append(
            {
                "day": f"Day {i}",

                "focus": focus,

                "warmup": [
                    "5 minutes easy walking",
                    "Dynamic mobility for major joints",
                ],

                "exercises": [
                    {
                        "name": "Bodyweight squat",
                        "sets": "3",
                        "reps_or_duration": "10-12 reps",
                        "rest": "60-90 sec",
                    },
                    {
                        "name": "Incline push-up",
                        "sets": "3",
                        "reps_or_duration": "8-12 reps",
                        "rest": "60-90 sec",
                    },
                    {
                        "name": "Brisk walk",
                        "sets": "1",
                        "reps_or_duration": "15-25 minutes",
                        "rest": "As needed",
                    },
                ],

                "cooldown": [
                    "5 minutes easy walking",
                    "Gentle stretching",
                ],
            }
        )

    return WorkoutPlan(
        title=(
            f"7-Day "
            f"{user.goal.replace('_', ' ').title()} Plan"
        ),

        summary=(
            f"A {user.intensity}-intensity "
            f"starter plan tailored to "
            f"{user.name}'s goal."
        ),

        days=days,

        safety_notes=[
            (
                "Use controlled form and adjust "
                "difficulty to your current ability."
            ),
            (
                "Stop if you experience pain, "
                "dizziness, chest pain, or unusual "
                "shortness of breath."
            ),
        ],
    )


def _generate_workout_request(
    client: genai.Client,
    model: str,
    prompt: str,
) -> WorkoutPlan:

    response = client.models.generate_content(

        model=model,

        contents=prompt,

        config=types.GenerateContentConfig(

            response_mime_type="application/json",

            response_schema=WorkoutPlan,

            temperature=0.4,

            max_output_tokens=3500,
        ),
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty workout plan."
        )

    return WorkoutPlan.model_validate_json(
        response.text
    )


def generate_workout_gemini(
    user: UserInput,
) -> WorkoutPlan:

    settings = get_settings()

    if settings.mock_ai:
        return _mock_plan(user)

    client = get_gemini_client()

    prompt = f"""
You are the workout-planning component of FitBuddy.

Create a safe, practical, personalized 7-day workout plan.

USER:

Name: {user.name}
Age: {user.age}
Weight: {user.weight_kg} kg
Goal: {user.goal}
Preferred intensity: {user.intensity}

REQUIREMENTS:

- Return exactly 7 days.
- Each day must contain a focus.
- Each day must contain warm-up exercises.
- Each day must contain main exercises.
- Each exercise must contain:
  name, sets, reps_or_duration, rest.
- Each day must contain cooldown activities.
- Include at least one recovery or mobility-oriented day.
- Keep intensity aligned with the selected level.
- Do not diagnose medical conditions.
- Do not prescribe medication.
- Do not prescribe supplements.
- Do not assume gym equipment.
- Prefer broadly accessible movements.
- Use clear beginner-friendly language.
- Include concise safety notes.
"""

    max_retries = 3
    base_delay = 5

    last_error = None

    for attempt in range(max_retries):

        try:

            return _generate_workout_request(
                client,
                settings.gemini_workout_model,
                prompt,
            )

        except Exception as exc:

            last_error = exc

            error_text = str(exc)

            # Retry only temporary server/capacity errors.
            is_temporary = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "500" in error_text
                or "INTERNAL" in error_text
                or "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
            )

            if not is_temporary:
                raise

            if attempt == max_retries - 1:
                break

            delay = base_delay * (2 ** attempt)

            time.sleep(delay)

    raise RuntimeError(
        "Gemini is temporarily unavailable after "
        f"{max_retries} attempts. "
        "Please wait a little and try again. "
        f"Last error: {last_error}"
    )