# NutriPulse

AI-powered nutrition assistant — IBM SkillsBuild / AICTE-2026 internship submission (Problem Statement #8: Nutrition Agent).

Generates personalised daily meal plans using **IBM Granite 3 8B Instruct** via **IBM watsonx.ai**.

---

## Prerequisites

- Python 3.11+
- An IBM Cloud account with a watsonx.ai project
- Your IBM Cloud IAM API key and watsonx.ai Project ID

---

## Setup

### 1. Clone / open the project

```bash
cd NutriPulse
```

### 2. Create your `.env` file

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env` and fill in your credentials:

```
WATSONX_API_KEY=your_ibm_cloud_iam_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

> **How to get these values:**
> 1. Log in to [IBM Cloud](https://cloud.ibm.com)
> 2. Go to **Manage → Access (IAM) → API keys** → Create an API key
> 3. Open [watsonx.ai](https://dataplatform.cloud.ibm.com) → Your project → **Manage** tab → copy the **Project ID**
> 4. `WATSONX_URL` is your region endpoint, e.g. `https://us-south.ml.cloud.ibm.com`

### 3. Install backend dependencies

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Start the backend

```bash
# From the backend/ directory, with venv active:
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### 5. Open the frontend

In a second terminal (no install needed):

```bash
python -m http.server 3000 --directory frontend
```

Open `http://localhost:3000` in your browser.

---

## How to Use

1. Fill in the profile form (age, goal, diet, budget, activity, allergies, preferences).
2. Click **Generate My Meal Plan** — Granite will return a full day's meals in ~15–30 seconds.
3. Review your plan on the next page.
4. Use the **feedback box** to refine (e.g. "replace paneer with tofu", "make lunch lighter").
5. Click **↺ Regenerate** for a fresh plan with the same profile.

---

## Project Structure

```
NutriPulse/
├── backend/
│   ├── main.py          # FastAPI app + all routes
│   ├── granite.py       # IBM watsonx.ai auth + Granite inference
│   ├── prompts.py       # All Granite prompt templates
│   ├── models.py        # Pydantic request/response models
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Profile form
│   ├── plan.html        # Meal plan + feedback
│   ├── style.css        # All styles
│   └── app.js           # All frontend logic
├── .env.example         # Credential template
└── AGENTS.md            # AI assistant guidance
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/meal-plan` | Generate meal plan from user profile |
| POST | `/feedback` | Revise existing plan based on feedback |

Full interactive docs at `http://localhost:8000/docs` when the server is running.

---

## Quick Test (curl)

```bash
curl http://localhost:8000/health
# → {"status":"ok"}

curl -X POST http://localhost:8000/meal-plan \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "age": 22,
    "goal": "weight_loss",
    "dietary_preference": "vegetarian",
    "budget": 300,
    "activity_level": "moderate",
    "allergies": [],
    "food_preferences": ["South Indian"]
  }'
```

---

## Technology

| Component | Technology |
|---|---|
| AI Model | IBM Granite 3 8B Instruct |
| AI Platform | IBM watsonx.ai |
| Backend | Python 3.11 + FastAPI |
| Frontend | Vanilla HTML / CSS / JS |
| AI Coding Assistant | IBM Bob |

---

## Notes

- Session data is stored in memory. Restarting the server clears all sessions.
- This is an MVP demo build — not for production use.
- IBM Bob was used throughout development: prompt engineering, model wrapper, API scaffolding, and frontend logic.
