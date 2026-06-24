import json
from groq import Groq
from src.config import GROQ_API_KEY
from src.models import UserProfile, FoodLog, ChatMessage
from src.nutrition_api import search_food
from src.database import log_food, save_user_profile, save_chat_message
from src.agents.planner import PlannerAgent
from src.agents.nutritionist import NutritionistAgent
from typing import List, Dict, Any

class SupervisorAgent:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        self.model = "llama-3.3-70b-versatile"
        self.planner = PlannerAgent()
        self.nutritionist = NutritionistAgent()

    def route_and_process(self, user_message: str, profile: UserProfile, todays_logs: List[FoodLog], chat_history: List[dict]) -> str:
        """
        Routes the user query, executes actions (such as logging food or recalculating goals),
        and returns the final assistant response.
        """
        if not self.client:
            return "Groq API key not set. Please add it to your .env file."

        system_prompt = (
            "You are the **Supervisor Agent** for a personalized Nutrition Coaching system. "
            "Your job is to analyze the user's chat message and classify their intent into one of these types:\n"
            "1. 'log_food': User is trying to record or log something they ate (e.g., 'I ate an egg', 'log 100g chicken', 'breakfast: oatmeal').\n"
            "2. 'replan': User wants to change their personal targets, goals, or recalculate their plan (e.g., 'recalculate my macros', 'I want to build muscle instead').\n"
            "3. 'chat': General nutrition questions, recipes, tips, or casual talk.\n\n"
            "IMPORTANT: If the user is logging food, extract the food name, quantity, and unit. "
            "Also provide a solid macro estimate for that item (calories in kcal, protein in g, carbs in g, fat in g) "
            "in case we need to fall back to an estimate if the database lookup fails.\n\n"
            "You MUST return your response as a valid JSON object matching this schema:\n"
            "{\n"
            '  "intent": "log_food" | "replan" | "chat",\n'
            '  "food_details": {\n'
            '    "food_name": string or null,\n'
            '    "quantity": number or null,\n'
            '    "unit": string or null\n'
            "  },\n"
            '  "estimate": {\n'
            '    "food_name": string or null,\n'
            '    "calories": number or null,\n'
            '    "protein": number or null,\n'
            '    "carbs": number or null,\n'
            '    "fat": number or null,\n'
            '    "serving_quantity": number or null,\n'
            '    "serving_unit": string or null\n'
            "  },\n"
            '  "routing_reason": string\n'
            "}"
        )

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(chat_completion.choices[0].message.content)
            intent = analysis.get("intent", "chat")
            
            if intent == "log_food":
                return self._handle_log_food(analysis, todays_logs)
                
            elif intent == "replan":
                return self._handle_replan(profile)
                
            else:
                # Delegate to Nutritionist for coaching / answering questions
                return self.nutritionist.respond(profile, todays_logs, chat_history, user_message)

        except Exception as e:
            # Fallback to general nutritionist if routing errors out
            print(f"Routing error: {e}")
            return self.nutritionist.respond(profile, todays_logs, chat_history, user_message)

    def _handle_log_food(self, analysis: Dict[str, Any], todays_logs: List[FoodLog]) -> str:
        """
        Attempts to search a food API. If found, logs from API.
        If API finds nothing, logs the supervisor's LLM macro estimate.
        """
        food_details = analysis.get("food_details", {})
        food_name = food_details.get("food_name")
        qty = food_details.get("quantity") or 1.0
        unit = food_details.get("unit") or "serving"
        
        if not food_name:
            return "I couldn't quite catch the name of the food you ate. Could you please specify what food and quantity you'd like to log?"

        # 1. Try public database API
        db_results = search_food(food_name)
        
        if db_results:
            match = db_results[0]
            # Adjust nutrition values based on logged quantity vs API base quantity
            base_qty = match.get("serving_quantity") or 100.0
            ratio = float(qty) / float(base_qty) if base_qty > 0 else 1.0
            
            # If the user specified a count like "2 eggs" and base unit is "g",
            # or if unit is generic, handle scaling carefully:
            if unit.lower() in ["serving", "piece", "unit", "egg", "apple", "banana"] and match.get("serving_unit", "").lower() in ["g", "ml"]:
                # If database returns 100g, assume 1 generic serving/piece is around 100g or use standard scale.
                # E.g., for eggs or fruit, let's trust LLM estimate scale if DB is standard 100g.
                # Actually, let's keep database base scaling:
                pass

            logged_calories = match["calories"] * ratio
            logged_protein = match["protein"] * ratio
            logged_carbs = match["carbs"] * ratio
            logged_fat = match["fat"] * ratio

            new_log = FoodLog(
                food_name=match["food_name"],
                calories=round(logged_calories, 1),
                protein=round(logged_protein, 1),
                carbs=round(logged_carbs, 1),
                fat=round(logged_fat, 1),
                serving_quantity=float(qty),
                serving_unit=unit
            )
            log_food(new_log)
            
            return (
                f"✅ **Logged from Database:**\n"
                f"Logged **{qty} {unit}** of **{match['food_name']}** ({match['source']})\n\n"
                f"**Nutrition breakdown:**\n"
                f"-  calories: `{new_log.calories} kcal`\n"
                f"- protein: `{new_log.protein}g`\n"
                f"- carbs: `{new_log.carbs}g`\n"
                f"- fat: `{new_log.fat}g`"
            )
            
        # 2. Fall back to LLM Estimate if API returns nothing
        est = analysis.get("estimate")
        if est and est.get("calories") is not None:
            # Scale LLM estimate based on user quantity
            est_base_qty = est.get("serving_quantity") or 1.0
            ratio = float(qty) / float(est_base_qty) if est_base_qty > 0 else 1.0
            
            new_log = FoodLog(
                food_name=est.get("food_name") or food_name,
                calories=round(float(est["calories"]) * ratio, 1),
                protein=round(float(est["protein"]) * ratio, 1),
                carbs=round(float(est["carbs"]) * ratio, 1),
                fat=round(float(est["fat"]) * ratio, 1),
                serving_quantity=float(qty),
                serving_unit=unit
            )
            log_food(new_log)
            
            return (
                f"🍳 **Logged via Agent Estimation:**\n"
                f"The public food database didn't have a clear match, so I estimated the macros for **{qty} {unit}** of **{new_log.food_name}**:\n\n"
                f"**Nutrition breakdown:**\n"
                f"- calories: `{new_log.calories} kcal`\n"
                f"- protein: `{new_log.protein}g`\n"
                f"- carbs: `{new_log.carbs}g`\n"
                f"- fat: `{new_log.fat}g`"
            )
            
        return f"Sorry, I couldn't log the food '{food_name}' because I was unable to retrieve a nutrition estimate. Please specify the grams or try again."

    def _handle_replan(self, profile: UserProfile) -> str:
        """
        Invokes the Planner agent to recalculate targets and saves them to the profile.
        """
        baselines = self.planner.calculate_baselines(profile)
        
        # Save new macros
        profile.target_calories = baselines["target_calories"]
        profile.target_protein = baselines["protein_g"]
        profile.target_carbs = baselines["carbs_g"]
        profile.target_fat = baselines["fat_g"]
        
        save_user_profile(profile)
        
        explanation = self.planner.generate_plan_explanation(profile, baselines)
        
        return (
            f"🔄 **Plan Recalculated!**\n\n"
            f"I have recalculated your personal daily targets based on your latest profile info:\n"
            f"- **Calories**: `{profile.target_calories} kcal`\n"
            f"- **Protein**: `{profile.target_protein}g`\n"
            f"- **Carbohydrates**: `{profile.target_carbs}g`\n"
            f"- **Fat**: `{profile.target_fat}g`\n\n"
            f"{explanation}"
        )
