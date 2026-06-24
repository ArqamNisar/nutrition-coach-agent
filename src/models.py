from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=1, primary_key=True)  # Single user model, default to ID 1
    age: int
    gender: str
    height: float  # cm
    weight: float  # kg
    activity_level: str  # Sedentary, Lightly Active, Moderately Active, Very Active, Extra Active
    diet_type: str  # Standard, Vegetarian, Vegan, Keto, Paleo, etc.
    allergies: str  # Text/comma-separated list of allergies & restrictions
    goal: str  # Lose Weight, Maintain Weight, Build Muscle, Improve General Health
    target_calories: Optional[float] = None
    target_protein: Optional[float] = None  # grams
    target_carbs: Optional[float] = None  # grams
    target_fat: Optional[float] = None  # grams
    updated_at: datetime = Field(default_factory=datetime.now)

class FoodLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now)
    food_name: str
    calories: float  # kcal
    protein: float  # grams
    carbs: float  # grams
    fat: float  # grams
    serving_quantity: float
    serving_unit: str  # e.g., grams, oz, pieces

class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now)
    role: str  # "user" or "assistant"
    agent_name: Optional[str] = None  # "supervisor", "planner", or "nutritionist"
    content: str
