"""
granite.py — IBM watsonx.ai auth + Granite 4 inference wrapper.

Model:    ibm/granite-4-h-small
Endpoint: /ml/v1/text/chat  (OpenAI-compatible chat completion)
Rules:
- This is the ONLY file that calls the watsonx.ai API.
- IAM token is cached at module level with expiry check.
- All calls are async (httpx.AsyncClient).
"""

import logging
import os
import re
import time
from typing import Any

import httpx
from dotenv import load_dotenv

from prompts import build_meal_plan_prompt, build_feedback_prompt, build_swap_prompt
from models import SwapMealResponse, UserProfile

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Copy .env.example to .env and fill in your IBM credentials."
        )
    return val

WATSONX_API_KEY: str    = _require_env("WATSONX_API_KEY")
WATSONX_PROJECT_ID: str = _require_env("WATSONX_PROJECT_ID")
WATSONX_URL: str        = _require_env("WATSONX_URL").rstrip("/")

MODEL_ID = "ibm/granite-4-h-small"
# /ml/v1/text/chat is the current (non-deprecated) endpoint for granite-4
GENERATION_ENDPOINT = f"{WATSONX_URL}/ml/v1/text/chat?version=2023-05-29"
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# Chat-API parameter names (max_tokens, not max_new_tokens; no repetition_penalty)
GENERATION_PARAMS: dict[str, Any] = {
    "max_tokens": 1024,
    "temperature": 0.7,
}

# ---------------------------------------------------------------------------
# IAM token cache
# ---------------------------------------------------------------------------

_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


async def _get_iam_token() -> str:
    """Return a valid IAM Bearer token, refreshing if expired."""
    now = time.time()
    # Refresh 60 seconds before expiry to avoid edge cases
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    logger.info("Refreshing IAM token")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            IAM_TOKEN_URL,
            # form-encoded — NOT JSON
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": WATSONX_API_KEY,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        payload = resp.json()

    _token_cache["access_token"] = payload["access_token"]
    # expires_in is in seconds from now
    _token_cache["expires_at"] = now + payload.get("expires_in", 3600)
    return _token_cache["access_token"]


# ---------------------------------------------------------------------------
# Core generation helper
# ---------------------------------------------------------------------------

async def _generate(system_prompt: str, user_prompt: str) -> str:
    """Send a chat request to Granite and return the generated text.

    Uses the /ml/v1/text/chat endpoint (OpenAI-compatible).
    Response shape: data["choices"][0]["message"]["content"]
    """
    token = await _get_iam_token()

    body = {
        "model_id": MODEL_ID,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "parameters": GENERATION_PARAMS,
        "project_id": WATSONX_PROJECT_ID,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            GENERATION_ENDPOINT,
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code != 200:
            # Log the actual API error so it appears in uvicorn output
            logger.error(
                "watsonx.ai error %d: %s",
                resp.status_code,
                resp.text[:500],
            )
        resp.raise_for_status()
        data = resp.json()

    generated: str = data["choices"][0]["message"]["content"].strip()
    logger.info("Granite response received (%d chars)", len(generated))
    return generated


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_meal_plan(profile: UserProfile) -> tuple[str, str]:
    """
    Generate a personalised daily meal plan for the given user profile.

    Returns:
        (meal_plan, explanation) — both plain text strings.
    """
    system_prompt, user_prompt = build_meal_plan_prompt(profile)
    raw = await _generate(system_prompt, user_prompt)

    # Split on the EXPLANATION marker inserted by the prompt template
    if "## EXPLANATION" in raw:
        parts = raw.split("## EXPLANATION", 1)
        meal_plan = parts[0].strip()
        explanation = parts[1].strip()
    else:
        meal_plan = raw
        explanation = "See meal plan above for details."

    return meal_plan, explanation


async def revise_meal_plan(
    profile: UserProfile,
    prior_plan: str,
    feedback_text: str,
) -> tuple[str, str]:
    """
    Revise an existing meal plan based on user feedback.

    Returns:
        (revised_meal_plan, explanation) — both plain text strings.
    """
    system_prompt, user_prompt = build_feedback_prompt(profile, prior_plan, feedback_text)
    raw = await _generate(system_prompt, user_prompt)

    if "## EXPLANATION" in raw:
        parts = raw.split("## EXPLANATION", 1)
        meal_plan = parts[0].strip()
        explanation = parts[1].strip()
    else:
        meal_plan = raw
        explanation = "Revised based on your feedback."

    return meal_plan, explanation


async def swap_meal(
    profile: UserProfile,
    meal_title: str,
    original_meal: str,
) -> SwapMealResponse:
    """
    Generate one smart alternative meal using Granite.

    Returns a SwapMealResponse with parsed nutrition fields.
    """
    system_prompt, user_prompt = build_swap_prompt(profile, meal_title, original_meal)
    raw = await _generate(system_prompt, user_prompt)

    # Parse the structured response — each field on its own line
    def _field(pattern: str) -> str:
        m = re.search(pattern, raw, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else ""

    return SwapMealResponse(
        meal_name     = _field(r"\*\*Meal:\*\*\s*(.+)"),
        ingredients   = _field(r"\*\*Ingredients:\*\*\s*(.+)"),
        calories      = _field(r"\*\*Calories:\*\*\s*([\d,]+\s*(?:kcal)?)"),
        protein       = _field(r"\*\*Protein:\*\*\s*([\d.]+\s*g?)"),
        carbs         = _field(r"\*\*Carbs:\*\*\s*([\d.]+\s*g?)"),
        fat           = _field(r"\*\*Fat:\*\*\s*([\d.]+\s*g?)"),
        estimated_cost= _field(r"\*\*Estimated cost:\*\*\s*[₹]?\s*([\d,]+)"),
        swap_reason   = _field(r"\*\*Swap reason:\*\*\s*(.+)"),
    )
