"""
prompts.py — ALL Granite prompt templates for NutriPulse.

Rules:
- This is the ONLY file that contains prompt strings.
- Each function returns a (system_prompt, user_prompt) tuple.
  granite.py places system in {"role":"system"} and user in {"role":"user"}.
- Prompt format uses explicit ## section headers — Granite 4 follows them reliably.
"""

from models import UserProfile

# ---------------------------------------------------------------------------
# System persona — used as the "system" role message in every chat call
# ---------------------------------------------------------------------------

SYSTEM_PERSONA = (
    "You are NutriPulse, an expert AI nutrition assistant. "
    "You create practical, affordable, and culturally respectful meal plans. "
    "You always provide calorie counts and macronutrients (protein, carbs, fat) "
    "for every meal. You never recommend foods the user is allergic to. "
    "Format your entire response using clear Markdown section headers (## Heading)."
)


# ---------------------------------------------------------------------------
# Health condition helper
# ---------------------------------------------------------------------------

_CONDITION_LABELS = {
    "diabetes":         "Diabetes",
    "hypertension":     "Hypertension (High Blood Pressure)",
    "high_cholesterol": "High Cholesterol",
    "other":            "Other health condition",
}

_CONDITION_GUIDANCE = {
    "diabetes": (
        "Prioritise low-glycaemic index foods, limit refined carbohydrates and added sugars, "
        "and include fibre-rich foods to help manage blood sugar."
    ),
    "hypertension": (
        "Recommend low-sodium options, include potassium-rich foods (bananas, spinach, lentils), "
        "and limit processed and salty foods."
    ),
    "high_cholesterol": (
        "Favour heart-healthy fats (olive oil, nuts, avocado), limit saturated fat, "
        "and include soluble-fibre foods (oats, legumes, fruits)."
    ),
    "other": (
        "Apply general healthy-eating principles: balanced macros, whole foods, and minimal processed items."
    ),
}

_SAFETY_NOTE = (
    "\nIMPORTANT: This meal plan is for general wellness guidance only and is NOT a substitute "
    "for professional medical or dietary advice. Please consult a registered dietitian or doctor "
    "before making significant dietary changes related to your health condition."
)


def _condition_text(condition: str) -> tuple[str, str]:
    """Return (profile_line, task_note) strings for the given health condition.

    profile_line — a bullet to embed in ## USER PROFILE (empty string if none).
    task_note    — guidance paragraph to embed before the format instructions
                   (empty string if condition is 'none').
    """
    key = (condition or "none").lower().strip()
    if key == "none" or key not in _CONDITION_LABELS:
        return "", ""

    label    = _CONDITION_LABELS[key]
    guidance = _CONDITION_GUIDANCE.get(key, "")
    profile_line = f"- Health condition: {label}\n"
    task_note = (
        f"\nHEALTH CONDITION CONSIDERATIONS ({label}):\n"
        f"{guidance}\n"
        f"{_SAFETY_NOTE}\n"
    )
    return profile_line, task_note


# ---------------------------------------------------------------------------
# Meal plan prompt
# ---------------------------------------------------------------------------

def build_meal_plan_prompt(profile: UserProfile) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for meal plan generation."""

    allergies_str = (
        ", ".join(profile.allergies) if profile.allergies else "None"
    )
    preferences_str = (
        ", ".join(profile.food_preferences) if profile.food_preferences else "None"
    )

    goal_labels = {
        "weight_loss":     "lose weight",
        "weight_gain":     "gain weight / build muscle",
        "maintenance":     "maintain current weight",
        "muscle_building": "build muscle mass",
        "better_health":   "improve overall health",
    }
    goal_text = goal_labels.get(profile.goal, profile.goal)

    activity_labels = {
        "sedentary":   "sedentary (desk job, little exercise)",
        "light":       "lightly active (1–2 days/week exercise)",
        "moderate":    "moderately active (3–5 days/week exercise)",
        "very_active": "very active (6–7 days/week hard exercise)",
        "athlete":     "athlete (twice-daily training)",
    }
    activity_text = activity_labels.get(profile.activity_level, profile.activity_level)

    condition_line, condition_note = _condition_text(profile.health_condition)

    user_prompt = f"""## USER PROFILE
- Age: {profile.age} years
- Goal: {goal_text}
- Dietary preference: {profile.dietary_preference}
- Daily food budget: ₹{profile.budget}
- Activity level: {activity_text}
- Allergies / intolerances: {allergies_str}
- Food preferences: {preferences_str}
{condition_line}
## TASK
Create a complete, personalised ONE-DAY meal plan for this user.
{condition_note}
Format your response EXACTLY as follows (use these exact ## headings):

## Breakfast
**Meal:** [meal name]
**Ingredients:** [list]
**Estimated cost:** ₹[amount]
**Calories:** [kcal] | **Protein:** [g] | **Carbs:** [g] | **Fat:** [g]
**Why this meal:** [one sentence explanation]

## Mid-Morning Snack
[same format]

## Lunch
[same format]

## Evening Snack
[same format]

## Dinner
[same format]

## Daily Totals
**Total Calories:** [kcal] | **Protein:** [g] | **Carbs:** [g] | **Fat:** [g]
**Total Estimated Cost:** ₹[amount]

## EXPLANATION
[2–3 sentences explaining how this plan supports the user's goal, respects their preferences, and stays within budget]{"" if not condition_note else chr(10) + "End with a one-sentence safety note: consult a registered dietitian for personalised advice on your health condition."}
"""
    return SYSTEM_PERSONA, user_prompt


# ---------------------------------------------------------------------------
# Feedback / revision prompt
# ---------------------------------------------------------------------------

def build_feedback_prompt(
    profile: UserProfile,
    prior_plan: str,
    feedback_text: str,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for meal plan revision."""

    allergies_str = (
        ", ".join(profile.allergies) if profile.allergies else "None"
    )
    condition_line, _ = _condition_text(profile.health_condition)

    user_prompt = f"""## USER PROFILE (unchanged)
- Age: {profile.age} | Goal: {profile.goal} | Diet: {profile.dietary_preference}
- Budget: ₹{profile.budget}/day | Activity: {profile.activity_level}
- Allergies: {allergies_str}
{condition_line}

[PREVIOUS PLAN]
{prior_plan}

[USER FEEDBACK]
{feedback_text}

[REVISED PLAN]
Revise the meal plan above to address the user's feedback while still meeting their
nutritional goals and staying within budget. Use the EXACT same format as the previous
plan (## Breakfast, ## Lunch, etc.).
End with a ## EXPLANATION section (2–3 sentences) describing what you changed and why.
"""
    return SYSTEM_PERSONA, user_prompt


# ---------------------------------------------------------------------------
# Smart food swap prompt
# ---------------------------------------------------------------------------

def build_swap_prompt(
    profile: "UserProfile",
    meal_title: str,
    original_meal: str,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a single-meal smart swap."""

    allergies_str = (
        ", ".join(profile.allergies) if profile.allergies else "None"
    )
    preferences_str = (
        ", ".join(profile.food_preferences) if profile.food_preferences else "None"
    )
    condition_line, _ = _condition_text(profile.health_condition)

    user_prompt = f"""## SWAP REQUEST

The user wants an alternative to their {meal_title}.

## ORIGINAL MEAL
{original_meal}

## USER PROFILE
- Goal: {profile.goal}
- Dietary preference: {profile.dietary_preference}
- Daily food budget: ₹{profile.budget}
- Activity level: {profile.activity_level}
- Allergies / intolerances: {allergies_str}
- Food preferences: {preferences_str}
{condition_line}

## TASK
Suggest ONE alternative meal for {meal_title} that:
- Is DIFFERENT from the original meal above
- Respects all dietary preferences and allergies
- Has similar or better calorie and protein content
- Fits within the daily food budget
- Suits the user's health goal

Respond ONLY with the following fields in EXACTLY this format (no extra text):

**Meal:** [meal name]
**Ingredients:** [comma-separated list]
**Calories:** [number] kcal
**Protein:** [number]g
**Carbs:** [number]g
**Fat:** [number]g
**Estimated cost:** ₹[number]
**Swap reason:** [one sentence explaining why this is a good swap]
"""
    return SYSTEM_PERSONA, user_prompt
