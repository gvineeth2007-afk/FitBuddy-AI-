# FitBuddy — AI Fitness Plan Generator

FitBuddy is a FastAPI + Jinja2 web application that generates personalized 7-day workout plans and nutrition/recovery tips with Google Gemini, stores users/plans in SQLite, and supports AI-powered plan revisions from feedback.

This implementation follows the supplied FitBuddy document's architecture and user flows, while using the current `google-genai` SDK and configurable model IDs.

## Features

- User profile form: name, user ID, age, weight, fitness goal, intensity.
- AI-generated 7-day workout plan.
- AI-generated nutrition/recovery tip.
- Feedback-based plan revision.
- SQLite persistence with SQLAlchemy.
- Admin dashboard for users and original/updated plans.
- REST API endpoints plus server-rendered HTML.
- Structured Gemini JSON output validated by Pydantic.
- Mock AI mode for testing without a Gemini API key.
- Input validation and basic safety messaging.

## Project structure

```text
FitBuddy/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── gemini_generator.py
│   ├── gemini_flash_generator.py
│   ├── updated_plan.py
│   ├── routes.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── result.html
│   │   ├── all_users.html
│   │   └── error.html
│   └── static/css/style.css
├── tests/
│   ├── __init__.py
│   └── test_app.py
├── .env.example
├── .gitignore
├── requirements.txt
├── run_windows.bat
└── README.md
```

## VS Code installation

Install Python 3.11+ and VS Code. Open the `FitBuddy` folder in VS Code.

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
.venv\Scripts\activate.bat
```

## Gemini configuration

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Set:

```env
GEMINI_API_KEY=your_key_here
```

The default model IDs are configurable:

```env
GEMINI_WORKOUT_MODEL=gemini-2.5-pro
GEMINI_FAST_MODEL=gemini-2.5-flash
```

If your Google AI account exposes different current model IDs, change those variables only.

For local testing without Gemini:

```env
MOCK_AI=true
```

## Run

```powershell
uvicorn app.main:app --reload
```

Open:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

Admin dashboard:

```text
http://127.0.0.1:8000/view-all-users?admin_key=change-me
```

Change `ADMIN_KEY` in `.env` first.

## Test

```powershell
pytest -q
```

Tests run with `MOCK_AI=true` and therefore do not use Gemini quota.

## API examples

### Health

```http
GET /api/health
```

### Generate

```http
POST /api/plans
Content-Type: application/json

{
  "user_id": "demo001",
  "name": "Alex",
  "age": 28,
  "weight_kg": 72,
  "goal": "muscle_gain",
  "intensity": "medium"
}
```

### Feedback

```http
POST /api/plans/demo001/feedback
Content-Type: application/json

{
  "feedback": "Add more cardio and one additional rest day."
}
```

### User

```http
GET /api/users/demo001
```

### Admin API

```http
GET /api/users?admin_key=change-me
```

## Troubleshooting

### Missing Gemini API key

Set `GEMINI_API_KEY` in `.env`, or use `MOCK_AI=true`.

### Model not found

Set `GEMINI_WORKOUT_MODEL` and `GEMINI_FAST_MODEL` to model IDs available to your Google AI account.

### Port already used

```powershell
uvicorn app.main:app --reload --port 8001
```

### Reset local database

Stop the server and delete `fitbuddy.db`, then start the application again.

## Safety

FitBuddy is an educational fitness-planning application, not a medical service. AI-generated exercise/nutrition content should be reviewed by an appropriate qualified professional where necessary. Do not store highly sensitive health information in this demo database.
