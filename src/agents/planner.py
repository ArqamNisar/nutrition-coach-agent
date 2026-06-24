import json
from groq import Groq
from src.config import GROQ_API_KEY
from src.models import UserProfile
from src.logger import get_logger

logger = get_logger(__name__)

class PlannerAgent:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        # Default model
        self.model = "llama-3.3-70b-versatile"
        logger.info("PlannerAgent initialized.")

    def calculate_baselines(self, profile: UserProfile) -> dict:
        """
        Calculates programmatic baseline caloric and macronutrient requirements.
        Uses Mifflin-St Jeor Equation.
        """
        logger.info(f"Calculating baseline requirements for user_id={profile.id} (Weight: {profile.weight}kg, Goal: {profile.goal}, Diet: {profile.diet_type})")
        # BMR calculation
        if profile.gender.lower() == "male":
            bmr = 10 * profile.weight + 6.25 * profile.height - 5 * profile.age + 5
        else:
            # Female or Other (uses female as a safe lower baseline)
            bmr = 10 * profile.weight + 6.25 * profile.height - 5 * profile.age - 161
            
        # Activity multipliers
        multipliers = {
            "sedentary": 1.2,
            "lightly active": 1.375,
            "moderately active": 1.55,
            "very active": 1.725,
            "extra active": 1.9
        }
        multiplier = multipliers.get(profile.activity_level.lower(), 1.2)
        tdee = bmr * multiplier
        
        # Target calories based on goal
        goal = profile.goal.lower()
        if "lose" in goal:
            target_calories = tdee - 500
            # Safety floor
            min_calories = 1500 if profile.gender.lower() == "male" else 1200
            target_calories = max(target_calories, min_calories)
        elif "build" in goal or "gain" in goal:
            target_calories = tdee + 300
        else:
            target_calories = tdee
            
        # Macronutrient allocation (Grams)
        # Protein: 2.0g/kg for muscle building, 1.6g/kg for weight loss (preserves muscle), 1.2g/kg for maintenance
        if "build" in goal or "muscle" in goal:
            protein_g = profile.weight * 2.0
        elif "lose" in goal:
            protein_g = profile.weight * 1.6
        else:
            protein_g = profile.weight * 1.2
            
        # Fat: 25% of calories
        fat_calories = target_calories * 0.25
        fat_g = fat_calories / 9
        
        # Carbs: Remaining calories
        protein_calories = protein_g * 4
        remaining_calories = target_calories - (protein_calories + fat_calories)
        carbs_g = max(remaining_calories / 4, 50.0) # Floor carbs at 50g for safety unless ketogenic
        
        # Keto adjustments
        if "keto" in profile.diet_type.lower():
            carbs_g = 30.0  # standard keto limit
            # Re-adjust fats to fill the rest
            fat_calories = target_calories - (protein_g * 4 + carbs_g * 4)
            fat_g = fat_calories / 9

        results = {
            "bmr": round(bmr),
            "tdee": round(tdee),
            "target_calories": round(target_calories),
            "protein_g": round(protein_g),
            "carbs_g": round(carbs_g),
            "fat_g": round(fat_g)
        }
        logger.info(f"Programmatic baselines calculated: {results}")
        return results

    def generate_plan_explanation(self, profile: UserProfile, baselines: dict) -> str:
        """
        Uses Groq LLM to explain the calculated parameters, provide dietary suggestions
        tailored to their goal, diet type, allergies, and activity level.
        """
        if not self.client:
            logger.warning("Groq client not initialized. Using raw baseline calculations placeholder.")
            return "Groq API key not set. Using raw baseline calculations. Adjust your .env to see a personalized plan write-up."

        system_prompt = (
            "You are the **Planner Agent**, a specialized agent of a multi-agent Nutrition Coaching team. "
            "Your job is to explain the daily caloric and macronutrient targets generated for a user, "
            "and suggest how they should split their meals based on their profile, diet type, and goals."
        )

        user_prompt = f"""
        User Profile:
        - Age: {profile.age}
        - Gender: {profile.gender}
        - Height: {profile.height} cm
        - Weight: {profile.weight} kg
        - Activity Level: {profile.activity_level}
        - Diet Type: {profile.diet_type}
        - Allergies / Restrictions: {profile.allergies}
        - Goal: {profile.goal}
        
        Programmatically Calculated Baselines:
        - BMR: {baselines['bmr']} kcal
        - TDEE: {baselines['tdee']} kcal
        - Target Calories: {baselines['target_calories']} kcal
        - Target Protein: {baselines['protein_g']}g
        - Target Carbs: {baselines['carbs_g']}g
        - Target Fats: {baselines['fat_g']}g
        
        Write a concise, professional explanation of these targets. Break down:
        1. Why these targets fit their specific goal ({profile.goal}) and activity level.
        2. Give 3-4 specific dietary suggestions matching their diet type ({profile.diet_type}) and respecting their allergies ({profile.allergies}).
        3. Recommend a breakdown of these macros across 3 meals + 1 snack (with estimated gram splits).
        
        Keep your response encouraging, clear, formatted in Markdown, and avoid dry generic templates.
        """

        try:
            logger.info("Calling Groq LLM for plan explanation generation.")
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=0.2,
                max_tokens=1000
            )
            logger.info("Plan explanation successfully generated.")
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating plan explanation via Groq: {e}", exc_info=True)
            return f"Error generating plan explanation via Groq: {e}\n\nBaselines calculated successfully:\n- Calories: {baselines['target_calories']} kcal\n- Protein: {baselines['protein_g']}g\n- Carbs: {baselines['carbs_g']}g\n- Fat: {baselines['fat_g']}g"

