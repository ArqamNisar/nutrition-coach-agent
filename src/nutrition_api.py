import requests
from typing import List, Dict, Any, Optional
from src.config import USDA_API_KEY
from src.logger import get_logger

logger = get_logger(__name__)

def search_open_food_facts(query: str) -> List[Dict[str, Any]]:
    """
    Searches Open Food Facts API (completely free, no key required).
    Ideal for branded/packaged food.
    """
    logger.info(f"Searching Open Food Facts API for: '{query}'")
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": "1",
        "action": "process",
        "json": "1",
        "page_size": 10
    }
    headers = {
        "User-Agent": "NutritionCoachAgent/1.0 (https://github.com/ArqamNisar/nutrition-coach-agent)"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=8)
        logger.info(f"Open Food Facts API response status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])
            results = []
            
            for prod in products:
                name = prod.get("product_name") or prod.get("product_name_en") or "Unknown Product"
                nutriments = prod.get("nutriments", {})
                
                # Open Food Facts returns nutriments per 100g/100ml
                kcal = nutriments.get("energy-kcal_100g") or nutriments.get("energy-kcal") or 0.0
                protein = nutriments.get("proteins_100g") or nutriments.get("proteins") or 0.0
                carbs = nutriments.get("carbohydrates_100g") or nutriments.get("carbohydrates") or 0.0
                fat = nutriments.get("fat_100g") or nutriments.get("fat") or 0.0
                
                results.append({
                    "source": "Open Food Facts",
                    "food_name": name,
                    "calories": float(kcal),
                    "protein": float(protein),
                    "carbs": float(carbs),
                    "fat": float(fat),
                    "serving_quantity": 100.0,
                    "serving_unit": "g",
                    "image_url": prod.get("image_front_thumb_url", ""),
                    "barcode": prod.get("code", "")
                })
            logger.info(f"Open Food Facts API returned {len(results)} items.")
            return results
    except Exception as e:
        logger.error(f"Error calling Open Food Facts API: {e}", exc_info=True)
    
    return []

def search_usda(query: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Searches USDA FoodData Central API (free, requires key).
    Ideal for raw ingredients and whole foods (e.g. apple, egg, breast of chicken).
    """
    logger.info(f"Searching USDA FoodData Central for: '{query}'")
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key": api_key,
        "query": query,
        "pageSize": 10
    }
    
    try:
        response = requests.get(url, params=params, timeout=8)
        logger.info(f"USDA API response status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            foods = data.get("foods", [])
            results = []
            
            for food in foods:
                name = food.get("description", "Unknown Food")
                nutrients = food.get("foodNutrients", [])
                
                kcal = 0.0
                protein = 0.0
                carbs = 0.0
                fat = 0.0
                
                for nutr in nutrients:
                    n_id = nutr.get("nutrientId")
                    n_name = nutr.get("nutrientName", "").lower()
                    n_value = nutr.get("value", 0.0)
                    u_name = nutr.get("unitName", "").lower()
                    
                    # Match energy/calories (ID 1008 is Energy in kcal)
                    if n_id == 1008 or (n_name == "energy" and u_name == "kcal"):
                        kcal = n_value
                    # Match protein (ID 1003)
                    elif n_id == 1003 or n_name == "protein":
                        protein = n_value
                    # Match carbohydrates (ID 1005)
                    elif n_id == 1005 or "carbohydrate" in n_name:
                        carbs = n_value
                    # Match total fat (ID 1004), avoiding saturated/trans fats overwriting it
                    elif n_id == 1004 or n_name == "total lipid (fat)":
                        fat = n_value
                
                # USDA nutrients are returned per 100g/100ml.
                # Setting base serving quantity to 100.0g ensures correct scaling ratios in views.
                results.append({
                    "source": "USDA FoodData Central",
                    "food_name": name,
                    "calories": float(kcal),
                    "protein": float(protein),
                    "carbs": float(carbs),
                    "fat": float(fat),
                    "serving_quantity": 100.0,
                    "serving_unit": "g",
                    "image_url": "",
                    "barcode": ""
                })
            logger.info(f"USDA API returned {len(results)} items.")
            return results
    except Exception as e:
        logger.error(f"Error calling USDA API: {e}", exc_info=True)
        
    return []

def search_food(query: str) -> List[Dict[str, Any]]:
    """
    Searches across configured APIs. If USDA_API_KEY is present,
    it queries USDA first. Otherwise it queries Open Food Facts.
    """
    if not query or len(query.strip()) < 2:
        logger.info(f"search_food query '{query}' is empty or too short. Skipping search.")
        return []
        
    results = []
    if USDA_API_KEY:
        logger.info("USDA API Key found. Querying USDA API first.")
        results = search_usda(query, USDA_API_KEY)
        
    # If no results from USDA or key not set, fallback to Open Food Facts
    if not results:
        if USDA_API_KEY:
            logger.info("No results from USDA API. Falling back to Open Food Facts API.")
        else:
            logger.info("USDA API Key not set. Querying Open Food Facts API directly.")
        results = search_open_food_facts(query)
        
    logger.info(f"search_food query '{query}' completed with {len(results)} total results.")
    return results

