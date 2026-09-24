from typing import Literal

from pydantic import BaseModel, Field, field_validator

Goal = Literal["weight_loss", "muscle_gain", "general_wellness", "flexibility"]
Intensity = Literal["low", "medium", "high"]


class UserInput(BaseModel):
    user_id: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=13, le=100)
    weight_kg: float = Field(gt=20, le=500)
    goal: Goal
    intensity: Intensity

    @field_validator("user_id", "name")
    @classmethod
    def clean_strings(cls, value: str) -> str:
        return " ".join(value.strip().split())


class FeedbackRequest(BaseModel):
    feedback: str = Field(min_length=3, max_length=2000)


class Exercise(BaseModel):
    name: str
    sets: str
    reps_or_duration: str
    rest: str


class DayPlan(BaseModel):
    day: str
    focus: str
    warmup: list[str]
    exercises: list[Exercise]
    cooldown: list[str]


class WorkoutPlan(BaseModel):
    title: str
    summary: str
    days: list[DayPlan] = Field(min_length=7, max_length=7)
    safety_notes: list[str] = Field(default_factory=list)


class NutritionTip(BaseModel):
    tip: str
    recovery_note: str
