# AGENTS.md

This file provides guidance to agents when working with code in this repository.

---

## Project

**NutriPulse** — AI-powered nutrition assistant MVP built for IBM SkillsBuild / AICTE-2026 internship (Problem Statement #8: Nutrition Agent). Two-day build window. Must be functional and demonstrable.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML/CSS/JS (no build step) |
| Backend | Python 3.11 + FastAPI |
| AI model | IBM Granite 3 8B Instruct (`ibm/granite-3-8b-instruct`) |
| AI platform | IBM watsonx.ai REST API |
| HTTP client | `httpx` (async) |
| Config | `python-dotenv` (.env file) |

**Never use OpenAI, Anthropic, or any non-IBM AI API.**

---

## Repository Layout

```
NutriPulse/
├── backend/
│   ├── main.py          # FastAPI app + all routes
│   ├── granite.py       # watsonx.ai auth + Granite inference wrapper
│   ├── prompts.py       # all Granite prompt templates
│   ├── models.py        # Pydantic request/response models
│   └── requirements.txt
├── frontend/
│   ├── index.html       # profile form (page 1)
│   ├── plan.html        # meal plan display + feedback (page 2)
│   ├── style.css
│   └── app.js           # fetch calls + DOM rendering
├── .env.example         # template — never commit .env
├── AGENTS.md
└── .bob/
    ├── rules-agent/AGENTS.md
    ├── rules-ask/AGENTS.md
    └── rules-plan/AGENTS.md
```

---

## Commands

```bash
# Backend — from repo root
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend — no build step; open in browser directly or serve with:
python -m http.server 3000 --directory frontend
```

**Single test (no test framework yet — manual curl):**
```bash
curl -X POST http://localhost:8000/meal-plan \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","age":25,"goal":"weight_loss","dietary_preference":"vegetarian","budget":300,"activity_level":"moderate","allergies":[],"food_preferences":[]}'
```

---

## Environment Variables

```
WATSONX_API_KEY=        # IBM Cloud IAM API key
WATSONX_PROJECT_ID=     # watsonx.ai project ID
WATSONX_URL=            # e.g. https://us-south.ml.cloud.ibm.com
```

Never hardcode credentials. Load via `python-dotenv` in `granite.py`.

---

## IBM Granite Integration (Critical)

- **Auth:** Exchange IBM Cloud IAM API key for a Bearer token via `POST https://iam.cloud.ibm.com/identity/token`. Token expires in 1 hour — refresh before each call or cache with expiry check.
- **Inference endpoint:** `POST {WATSONX_URL}/ml/v1/text/generation?version=2023-05-29`
- **Required body fields:** `model_id`, `input`, `parameters` (`max_new_tokens`, `temperature`, `repetition_penalty`), `project_id`
- **Recommended params:** `max_new_tokens: 1024`, `temperature: 0.7`, `repetition_penalty: 1.1`
- All Granite logic lives in `backend/granite.py`. All prompts live in `backend/prompts.py`. Routes in `main.py` call granite functions only — no inline prompt strings.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/meal-plan` | Accept UserProfile → call Granite → return meal plan |
| POST | `/feedback` | Accept prior plan + feedback text → re-call Granite → return revised plan |
| GET | `/health` | Returns `{"status": "ok"}` |

Session state (profile + last plan) stored in a server-side Python dict keyed by `session_id` (UUID generated client-side, stored in `localStorage`). No database.

---

## Code Style

- Python: follow PEP 8; use type hints on all function signatures; async/await throughout FastAPI routes and `httpx` calls.
- Pydantic models in `models.py` — all request/response bodies must have a Pydantic model (no raw dicts in routes).
- Frontend JS: no frameworks; plain `fetch` with `async/await`; keep all API calls in `app.js`.
- No console.log left in final code; no print() left in final Python code (use logging).

---

## Constraints

- No database (SQLite, Postgres, Redis, etc.) — in-memory session dict only.
- No Docker required for MVP.
- No React, Vue, or npm — vanilla HTML/CSS/JS only.
- Two-day window: every addition must be justified by demo requirements.
