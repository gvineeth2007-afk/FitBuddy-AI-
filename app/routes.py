from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .gemini_flash_generator import generate_nutrition_tip_with_flash
from .gemini_generator import generate_workout_gemini
from .models import Plan, User
from .schemas import FeedbackRequest, UserInput
from .updated_plan import update_workout_plan

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _get_user_or_404(db: Session, user_id: str) -> User:
    user = db.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


def _get_latest_plan(db: Session, user_id: str) -> Plan:
    plan = db.scalar(select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc()))
    if not plan:
        raise HTTPException(status_code=404, detail="Workout plan not found.")
    return plan


def _user_dict(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "name": user.name,
        "age": user.age,
        "weight_kg": user.weight_kg,
        "goal": user.goal,
        "intensity": user.intensity,
    }


def _safe_json_load(value: str):
    return json.loads(value)


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "FitBuddy"},
    )


@router.post("/generate-workout")
def generate_workout_form(
    request: Request,
    user_id: str = Form(...),
    name: str = Form(...),
    age: int = Form(...),
    weight_kg: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user_input = UserInput(
            user_id=user_id,
            name=name,
            age=age,
            weight_kg=weight_kg,
            goal=goal,
            intensity=intensity,
        )
        workout = generate_workout_gemini(user_input)
        tip = generate_nutrition_tip_with_flash(user_input)

        user = db.scalar(select(User).where(User.user_id == user_input.user_id))
        if user is None:
            user = User(**user_input.model_dump())
            db.add(user)
        else:
            for key, value in user_input.model_dump().items():
                setattr(user, key, value)

        plan = db.scalar(select(Plan).where(Plan.user_id == user_input.user_id).order_by(Plan.created_at.desc()))
        if plan:
            plan.original_plan = workout.model_dump_json(indent=2)
            plan.updated_plan = None
            plan.feedback = None
            plan.nutrition_tip = tip.model_dump_json(indent=2)
        else:
            db.add(
                Plan(
                    user_id=user_input.user_id,
                    original_plan=workout.model_dump_json(indent=2),
                    nutrition_tip=tip.model_dump_json(indent=2),
                )
            )
        db.commit()

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "title": "Your FitBuddy Plan",
                "user": _user_dict(user),
                "workout_plan": workout.model_dump(),
                "nutrition_tip": tip.model_dump(),
                "updated": False,
                "message": None,
            },
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Plan generation failed")
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"title": "Plan generation failed", "message": str(exc)},
            status_code=500,
        )


@router.post("/submit-feedback")
def submit_feedback_form(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        feedback_request = FeedbackRequest(feedback=feedback)
        user = _get_user_or_404(db, user_id)
        plan = _get_latest_plan(db, user_id)
        user_input = UserInput(
            user_id=user.user_id,
            name=user.name,
            age=user.age,
            weight_kg=user.weight_kg,
            goal=user.goal,
            intensity=user.intensity,
        )
        revised = update_workout_plan(user_input, plan.original_plan, feedback_request.feedback)
        plan.updated_plan = revised.model_dump_json(indent=2)
        plan.feedback = feedback_request.feedback
        db.commit()

        tip = _safe_json_load(plan.nutrition_tip)
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "title": "Revised FitBuddy Plan",
                "user": _user_dict(user),
                "workout_plan": revised.model_dump(),
                "nutrition_tip": tip,
                "updated": True,
                "message": "Your plan was updated using your feedback.",
            },
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Feedback update failed")
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"title": "Feedback update failed", "message": str(exc)},
            status_code=500,
        )


@router.get("/view-all-users")
def view_all_users(request: Request, admin_key: str | None = None, db: Session = Depends(get_db)):
    settings = get_settings()
    if admin_key != settings.admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    records = []
    for user in users:
        plan = db.scalar(select(Plan).where(Plan.user_id == user.user_id).order_by(Plan.created_at.desc()))
        records.append({
            "user": user,
            "plan": plan,
            "original_plan": _safe_json_load(plan.original_plan) if plan else None,
            "updated_plan": _safe_json_load(plan.updated_plan) if plan and plan.updated_plan else None,
        })

    return templates.TemplateResponse(
        request=request,
        name="all_users.html",
        context={"title": "FitBuddy Admin", "records": records},
    )


@router.get("/api/health")
def health():
    return {"status": "ok", "service": "FitBuddy"}


@router.post("/api/plans")
def api_generate_plan(payload: UserInput, db: Session = Depends(get_db)):
    try:
        workout = generate_workout_gemini(payload)
        tip = generate_nutrition_tip_with_flash(payload)

        user = db.scalar(select(User).where(User.user_id == payload.user_id))
        if user is None:
            user = User(**payload.model_dump())
            db.add(user)
        else:
            for key, value in payload.model_dump().items():
                setattr(user, key, value)

        plan = db.scalar(select(Plan).where(Plan.user_id == payload.user_id).order_by(Plan.created_at.desc()))
        if plan is None:
            plan = Plan(
                user_id=payload.user_id,
                original_plan=workout.model_dump_json(indent=2),
                nutrition_tip=tip.model_dump_json(indent=2),
            )
            db.add(plan)
        else:
            plan.original_plan = workout.model_dump_json(indent=2)
            plan.updated_plan = None
            plan.feedback = None
            plan.nutrition_tip = tip.model_dump_json(indent=2)

        db.commit()
        return {
            "user": _user_dict(user),
            "workout_plan": workout.model_dump(),
            "nutrition_tip": tip.model_dump(),
            "updated": False,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/plans/{user_id}/feedback")
def api_update_plan(user_id: str, payload: FeedbackRequest, db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    plan = _get_latest_plan(db, user_id)
    user_input = UserInput(
        user_id=user.user_id,
        name=user.name,
        age=user.age,
        weight_kg=user.weight_kg,
        goal=user.goal,
        intensity=user.intensity,
    )

    try:
        revised = update_workout_plan(user_input, plan.original_plan, payload.feedback)
        plan.updated_plan = revised.model_dump_json(indent=2)
        plan.feedback = payload.feedback
        db.commit()
        return {
            "user": _user_dict(user),
            "workout_plan": revised.model_dump(),
            "nutrition_tip": _safe_json_load(plan.nutrition_tip),
            "updated": True,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/users/{user_id}")
def api_get_user(user_id: str, db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    plan = _get_latest_plan(db, user_id)
    return {
        "user": _user_dict(user),
        "original_plan": _safe_json_load(plan.original_plan),
        "updated_plan": _safe_json_load(plan.updated_plan) if plan.updated_plan else None,
        "nutrition_tip": _safe_json_load(plan.nutrition_tip),
        "feedback": plan.feedback,
    }


@router.get("/api/users")
def api_get_users(admin_key: str | None = None, db: Session = Depends(get_db)):
    settings = get_settings()
    if admin_key != settings.admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key.")
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return {"users": [_user_dict(user) for user in users]}
