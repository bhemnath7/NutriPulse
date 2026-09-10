from pydantic import BaseModel


class UserProfile(BaseModel):
    session_id: str
    age: int
    goal: str
    dietary_preference: str
    budget: float
    activity_level: str
    allergies: list[str]
    food_preferences: list[str]
    health_condition: str = "none"   # "none" | "diabetes" | "hypertension" | "high_cholesterol" | "other"


class FeedbackRequest(BaseModel):
    session_id: str
    feedback_text: str


class MealPlanResponse(BaseModel):
    session_id: str
    meal_plan: str
    explanation: str


class SwapMealRequest(BaseModel):
    session_id: str
    meal_title: str       # e.g. "Breakfast", "Lunch" — for context only
    original_meal: str    # the full original meal text block


class SwapMealResponse(BaseModel):
    meal_name: str
    ingredients: str
    calories: str
    protein: str
    carbs: str
    fat: str
    estimated_cost: str
    swap_reason: str
