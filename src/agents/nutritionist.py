from groq import Groq
from src.config import GROQ_API_KEY
from src.models import UserProfile, FoodLog
from src.logger import get_logger
from typing import List

logger = get_logger(__name__)

class NutritionistAgent:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        self.model = "llama-3.3-70b-versatile"
        logger.info("NutritionistAgent initialized.")

    def respond(self, profile: UserProfile, todays_logs: List[FoodLog], chat_history: List[dict], user_message: str) -> str:
        """
        Formulates a coaching response regarding user nutrition queries, recipes, and food logging.
        """
        logger.info(f"Nutritionist respond triggered. Todays logs: {len(todays_logs)} items. Chat history size: {len(chat_history)} messages.")
        if not self.client:
            logger.warning("Groq client not initialized (missing API key). Nutritionist respond aborted.")
            return "Groq API key not set. Please add it to your .env file to talk to the Nutritionist Coach."

        # Compile summaries of today's nutrients
        total_cal = sum(log.calories for log in todays_logs)
        total_protein = sum(log.protein for log in todays_logs)
        total_carbs = sum(log.carbs for log in todays_logs)
        total_fat = sum(log.fat for log in todays_logs)

        logged_foods_str = "\n".join([
            f"- {log.food_name}: {log.calories} kcal, P: {log.protein}g, C: {log.carbs}g, F: {log.fat}g (Qty: {log.serving_quantity} {log.serving_unit})"
            for log in todays_logs
        ]) if todays_logs else "No foods logged yet today."

        # System message setting the agent persona
        system_prompt = (
            "You are the **Nutritionist Agent**, a friendly, expert nutrition coach and meal advisor. "
            "Your partner is the **Planner Agent**, who defines the client's macro goals. "
            "Your job is to answer the user's questions, suggest recipes, review their daily logs, "
            "point out macro gaps, and keep them motivated. "
            "Always keep the user's profile, goal, allergies, and daily targets in mind. "
            "If they ask for recipes, ensure they are 100% compliant with their diet type and allergies. "
            "Provide helpful, practical tips, and structure your responses with clean Markdown headers and bullet points. "
            "Keep the tone encouraging, empathetic, and professional."
        )

        # Context details
        context = f"""
        User Profile:
        - Age: {profile.age}
        - Gender: {profile.gender}
        - Height: {profile.height} cm
        - Weight: {profile.weight} kg
        - Goal: {profile.goal}
        - Diet Type: {profile.diet_type}
        - Allergies / Restrictions: {profile.allergies}
        
        Daily Nutrition Targets:
        - Target Calories: {profile.target_calories} kcal
        - Target Protein: {profile.target_protein}g
        - Target Carbs: {profile.target_carbs}g
        - Target Fats: {profile.target_fat}g
        
        Logged Foods Today:
        {logged_foods_str}
        
        Current Nutrient Totals Today:
        - Calories: {total_cal:.1f} / {profile.target_calories or 0} kcal
        - Protein: {total_protein:.1f} / {profile.target_protein or 0}g
        - Carbs: {total_carbs:.1f} / {profile.target_carbs or 0}g
        - Fats: {total_fat:.1f} / {profile.target_fat or 0}g
        """

        # Build chat list
        messages = [{"role": "system", "content": system_prompt + "\n\n### USER CONTEXT ###\n" + context}]
        
        # Add history (last 10 messages for context)
        for msg in chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Add the active user message
        messages.append({"role": "user", "content": user_message})

        try:
            logger.info("Calling Groq LLM for Nutritionist response.")
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=1000
            )
            logger.info("Nutritionist response generated successfully.")
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error talking to Nutritionist Agent: {e}", exc_info=True)
            return f"Error talking to Nutritionist Agent: {e}"

