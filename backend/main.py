"""
main.py — FastAPI application for NutriPulse.

Routes:
  GET  /health       — liveness check
  POST /meal-plan    — generate meal plan from user profile
  POST /feedback     — revise meal plan based on user feedback
  POST /swap-meal    — generate one smart alternative for a single meal

Session state is stored in the module-level `sessions` dict keyed by session_id.
No database is used.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from granite import generate_meal_plan, revise_meal_plan, swap_meal
from models import FeedbackRequest, MealPlanResponse, SwapMealRequest, SwapMealResponse, UserProfile

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NutriPulse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files at /
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# ---------------------------------------------------------------------------
# In-memory session store  { session_id: { "profile": ..., "last_plan": ... } }
# ---------------------------------------------------------------------------

sessions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/meal-plan", response_model=MealPlanResponse)
async def create_meal_plan(profile: UserProfile) -> MealPlanResponse:
    """Accept a user profile, call Granite, return a personalised meal plan."""
    logger.info("Generating meal plan for session %s", profile.session_id)

    try:
        meal_plan, explanation = await generate_meal_plan(profile)
    except Exception as exc:
        logger.exception("Granite call failed: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"detail": "AI service unavailable. Please try again."},
        )

    # Persist profile + plan for the feedback endpoint
    sessions[profile.session_id] = {
        "profile": profile,
        "last_plan": meal_plan,
    }

    return MealPlanResponse(
        session_id=profile.session_id,
        meal_plan=meal_plan,
        explanation=explanation,
    )


@app.post("/feedback", response_model=MealPlanResponse)
async def submit_feedback(request: FeedbackRequest) -> MealPlanResponse:
    """Accept feedback on the current plan and return a revised version."""
    logger.info("Processing feedback for session %s", request.session_id)

    session = sessions.get(request.session_id)
    if not session:
        return JSONResponse(
            status_code=404,
            content={"detail": "Session not found. Please generate a meal plan first."},
        )

    profile: UserProfile = session["profile"]
    prior_plan: str = session["last_plan"]

    try:
        revised_plan, explanation = await revise_meal_plan(
            profile, prior_plan, request.feedback_text
        )
    except Exception as exc:
        logger.exception("Granite revision failed: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"detail": "AI service unavailable. Please try again."},
        )

    # Update stored plan with the revised version
    sessions[request.session_id]["last_plan"] = revised_plan

    return MealPlanResponse(
        session_id=request.session_id,
        meal_plan=revised_plan,
        explanation=explanation,
    )


@app.post("/swap-meal", response_model=SwapMealResponse)
async def swap_meal_endpoint(request: SwapMealRequest) -> SwapMealResponse:
    """Generate one smart alternative for a single meal in the current plan."""
    logger.info(
        "Swapping %s for session %s", request.meal_title, request.session_id
    )

    session = sessions.get(request.session_id)
    if not session:
        return JSONResponse(
            status_code=404,
            content={"detail": "Session not found. Please generate a meal plan first."},
        )

    profile: UserProfile = session["profile"]

    try:
        result = await swap_meal(profile, request.meal_title, request.original_meal)
    except Exception as exc:
        logger.exception("Granite swap failed: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"detail": "Couldn't generate a swap. Try again."},
        )

    return result
