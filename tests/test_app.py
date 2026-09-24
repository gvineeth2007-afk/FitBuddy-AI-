import os
from pathlib import Path

os.environ["MOCK_AI"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_fitbuddy.db"
os.environ["ADMIN_KEY"] = "test-admin"

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    path = Path("test_fitbuddy.db")
    if path.exists():
        path.unlink()


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generate_plan_api():
    payload = {
        "user_id": "test001",
        "name": "Test User",
        "age": 30,
        "weight_kg": 70,
        "goal": "general_wellness",
        "intensity": "medium",
    }
    response = client.post("/api/plans", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["workout_plan"]["days"]) == 7
    assert data["nutrition_tip"]["tip"]


def test_feedback_api():
    response = client.post(
        "/api/plans/test001/feedback",
        json={"feedback": "Add more cardio and an extra recovery day."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] is True
    assert len(data["workout_plan"]["days"]) == 7


def test_get_user():
    response = client.get("/api/users/test001")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["user_id"] == "test001"
    assert data["updated_plan"] is not None


def test_admin_requires_key():
    assert client.get("/api/users").status_code == 403
    assert client.get("/api/users?admin_key=test-admin").status_code == 200
