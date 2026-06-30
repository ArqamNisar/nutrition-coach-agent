import streamlit as st
import datetime
from src.models import UserProfile, FoodLog, ChatMessage, MealPlan
from src.database import save_user_profile, get_user_profile, log_food, get_todays_food_logs, delete_food_log, save_chat_message, get_chat_history, clear_chat_history, get_current_meal_plan, save_meal_plan
from src.agents.planner import PlannerAgent
from src.agents.supervisor import SupervisorAgent
from src.nutrition_api import search_food
from src.logger import get_logger

logger = get_logger(__name__)

# Initialize Agents
planner_agent = PlannerAgent()
supervisor_agent = SupervisorAgent()

def load_css():
    """Loads the custom CSS file for premium styling."""
    try:
        with open("src/style.css", "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            logger.info("Successfully loaded custom CSS stylesheet.")
    except Exception as e:
        logger.error(f"Error loading CSS: {e}", exc_info=True)

def render_progress_bar(label: str, current: float, target: float, color: str, unit: str = "g"):
    """Renders a custom styled macro progress bar."""
    pct = min((current / target) * 100, 100.0) if target > 0 else 0.0
    st.markdown(
        f"""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-weight: 500; font-size: 0.9rem;">
                <span>{label}</span>
                <span>{current:.1f} / {target:.0f} {unit} ({pct:.1f}%)</span>
            </div>
            <div class="macro-progress-container">
                <div class="macro-progress-bar" style="width: {pct}%; background: {color};"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_onboarding():
    """Renders the user onboarding form."""
    st.markdown("<h2 class='gradient-text'>👋 Welcome to your AI Nutrition Coach</h2>", unsafe_allow_html=True)
    st.markdown("<p class='sub-text'>Let's set up your profile to calculate your personalized nutrition targets.</p>", unsafe_allow_html=True)
    
    with st.form("onboarding_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=12, max_value=100, value=25, step=1)
            gender = st.selectbox("Gender", ["Female", "Male", "Other"])
            height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=170.0, step=0.5)
            weight = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=70.0, step=0.5)
            
        with col2:
            activity = st.selectbox(
                "Activity Level",
                ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extra Active"],
                index=0,
                help="Sedentary: Little to no exercise\nLightly Active: Light exercise 1-3 days/week\nModerately Active: Moderate exercise 3-5 days/week\nVery Active: Hard exercise 6-7 days/week\nExtra Active: Very hard daily exercise/physical job"
            )
            diet_type = st.selectbox(
                "Diet Type / Preferences",
                ["Standard/Anything", "Vegetarian", "Vegan", "Keto", "Paleo", "Mediterranean", "Low-Carb"]
            )
            allergies = st.text_input("Allergies or Dietary Restrictions", placeholder="e.g., Peanut allergy, Gluten-free, Lactose intolerant")
            goal = st.selectbox(
                "Fitness & Health Goal",
                ["Lose Weight", "Maintain Weight", "Build Muscle", "Improve General Health"]
            )
            
        submit = st.form_submit_button("Generate My Personalized Plan")
        
        if submit:
            logger.info(f"UI Onboarding form submitted. Age: {age}, Gender: {gender}, Height: {height}cm, Weight: {weight}kg, Activity: {activity}, Diet: {diet_type}, Goal: {goal}")
            # Create profile object
            profile = UserProfile(
                id=1,
                age=age,
                gender=gender,
                height=height,
                weight=weight,
                activity_level=activity,
                diet_type=diet_type,
                allergies=allergies if allergies.strip() else "None",
                goal=goal
            )
            
            # Calculate plan
            with st.spinner("Calculating nutritional targets with the Planner Agent..."):
                logger.info("Recalculating plan targets programmatically through PlannerAgent.")
                baselines = planner_agent.calculate_baselines(profile)
                profile.target_calories = baselines["target_calories"]
                profile.target_protein = baselines["protein_g"]
                profile.target_carbs = baselines["carbs_g"]
                profile.target_fat = baselines["fat_g"]
                
                # Save to database
                logger.info("Saving newly onboarding user profile to database.")
                save_user_profile(profile)
                
                # Get Explanation from Groq LLM
                explanation = planner_agent.generate_plan_explanation(profile, baselines)
                
                # Create intro chat messages
                logger.info("Initializing chat history with generated plan explanation.")
                save_chat_message(ChatMessage(role="assistant", content=f"Hello! I am your AI Nutrition Coach. Based on your inputs, we have generated your personalized meal and macro plan:\n\n{explanation}"))
                
            st.success("Plan Generated Successfully!")
            st.rerun()

def render_dashboard(profile: UserProfile):
    """Renders the dashboard with daily logs and target rings."""
    logger.info("Rendering daily nutrition dashboard.")
    st.markdown("<h2 class='gradient-text'>📊 Daily Nutrition Dashboard</h2>", unsafe_allow_html=True)
    
    # Fetch today's food logs
    todays_logs = get_todays_food_logs()
    
    # Calculate daily totals
    tot_calories = sum(l.calories for l in todays_logs)
    tot_protein = sum(l.protein for l in todays_logs)
    tot_carbs = sum(l.carbs for l in todays_logs)
    tot_fat = sum(l.fat for l in todays_logs)
    
    # Top metrics display
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Calories Consumed", f"{tot_calories:.0f} kcal", f"Target: {profile.target_calories:.0f}")
    with col2:
        st.metric("Protein", f"{tot_protein:.1f} g", f"Target: {profile.target_protein:.0f}")
    with col3:
        st.metric("Carbs", f"{tot_carbs:.1f} g", f"Target: {profile.target_carbs:.0f}")
    with col4:
        st.metric("Fat", f"{tot_fat:.1f} g", f"Target: {profile.target_fat:.0f}")
        
    st.markdown("---")
    
    # Progress Section
    st.markdown("### Today's Targets Progress")
    render_progress_bar("Calories", tot_calories, profile.target_calories or 2000.0, "linear-gradient(90deg, #06b6d4, #10b981)", "kcal")
    render_progress_bar("Protein", tot_protein, profile.target_protein or 120.0, "#ef4444")
    render_progress_bar("Carbohydrates", tot_carbs, profile.target_carbs or 200.0, "#f59e0b")
    render_progress_bar("Fats", tot_fat, profile.target_fat or 70.0, "#10b981")
    
    st.markdown("---")
    
    col_log, col_add = st.columns([3, 2])
    
    with col_log:
        st.markdown("### Today's Food Logs")
        if not todays_logs:
            st.info("No foods logged today yet. Try searching for food, logging it manually, or chatting with the AI Coach to log it!")
        else:
            for food in todays_logs:
                # Flex container for food item
                col_item, col_del = st.columns([5, 1])
                with col_item:
                    st.markdown(
                        f"""
                        <div class="food-log-item" style="margin: 0; padding: 10px 15px;">
                            <strong>{food.food_name}</strong> - {food.calories:.0f} kcal<br/>
                            <span class="badge badge-protein">P: {food.protein:.1f}g</span>
                            <span class="badge badge-carbs">C: {food.carbs:.1f}g</span>
                            <span class="badge badge-fat">F: {food.fat:.1f}g</span>
                            <span style="font-size:0.8rem; color:#94a3b8; float:right;">{food.serving_quantity:.1f} {food.serving_unit}</span>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                with col_del:
                    # Vertical alignment trick for Streamlit button
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_{food.id}", help="Delete log"):
                        logger.info(f"UI deletion action triggered for food log ID: {food.id} ('{food.food_name}')")
                        delete_food_log(food.id)
                        st.success("Deleted!")
                        st.rerun()
                        
    with col_add:
        st.markdown("### Search & Log Food")
        search_query = st.text_input("Search Food Database", placeholder="e.g. Greek yogurt, Chicken breast")
        
        if search_query:
            logger.info(f"UI food search triggered for: '{search_query}'")
            with st.spinner("Searching public nutrition databases..."):
                results = search_food(search_query)
                
            if not results:
                st.warning("No matches found. Try entering macros manually below or chat with the AI Coach.")
            else:
                for idx, item in enumerate(results[:5]):
                    with st.expander(f"{item['food_name']} ({item['source']})"):
                        st.markdown(
                            f"**Per {item['serving_quantity']} {item['serving_unit']}:**\n"
                            f"- Calories: {item['calories']:.1f} kcal\n"
                            f"- Protein: {item['protein']:.1f}g | Carbs: {item['carbs']:.1f}g | Fat: {item['fat']:.1f}g"
                        )
                        # Input quantity
                        qty = st.number_input(f"Quantity ({item['serving_unit']})", min_value=0.1, value=float(item['serving_quantity']), key=f"qty_{idx}")
                        if st.button("Log Food Item", key=f"add_{idx}"):
                            logger.info(f"UI Log Food button clicked for API search result: '{item['food_name']}', qty={qty} {item['serving_unit']}")
                            # Scale values
                            ratio = qty / item['serving_quantity']
                            new_log = FoodLog(
                                food_name=item['food_name'],
                                calories=round(item['calories'] * ratio, 1),
                                protein=round(item['protein'] * ratio, 1),
                                carbs=round(item['carbs'] * ratio, 1),
                                fat=round(item['fat'] * ratio, 1),
                                serving_quantity=qty,
                                serving_unit=item['serving_unit']
                            )
                            log_food(new_log)
                            st.success(f"Logged {item['food_name']}!")
                            st.rerun()
                            
        st.markdown("#### Quick Manual Add")
        with st.expander("Log Custom Food manually"):
            with st.form("manual_add_form"):
                m_name = st.text_input("Food Name", value="Custom Food")
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    m_cal = st.number_input("Calories (kcal)", min_value=0.0, value=100.0)
                    m_prot = st.number_input("Protein (g)", min_value=0.0, value=10.0)
                with col_m2:
                    m_carbs = st.number_input("Carbs (g)", min_value=0.0, value=10.0)
                    m_fat = st.number_input("Fat (g)", min_value=0.0, value=2.0)
                
                col_m3, col_m4 = st.columns(2)
                with col_m3:
                    m_qty = st.number_input("Quantity", min_value=0.1, value=1.0)
                with col_m4:
                    m_unit = st.text_input("Unit", value="serving")
                    
                m_submit = st.form_submit_button("Add Custom Food")
                if m_submit:
                    logger.info(f"UI Manual Log form submitted: name='{m_name}', calories={m_cal}, P/C/F={m_prot}/{m_carbs}/{m_fat}, qty={m_qty} {m_unit}")
                    new_log = FoodLog(
                        food_name=m_name,
                        calories=m_cal,
                        protein=m_prot,
                        carbs=m_carbs,
                        fat=m_fat,
                        serving_quantity=m_qty,
                        serving_unit=m_unit
                    )
                    log_food(new_log)
                    st.success(f"Logged {m_name}!")
                    st.rerun()

def render_coach(profile: UserProfile):
    """Renders the AI Coach Chat tab."""
    logger.info("Rendering AI Coach Chat tab.")
    st.markdown("<h2 class='gradient-text'>💬 AI Nutrition Coach</h2>", unsafe_allow_html=True)
    st.markdown("<p class='sub-text'>Ask questions, get recipes, or log foods simply by telling your Coach what you ate!</p>", unsafe_allow_html=True)
    
    # Retrieve today's logs and chat history
    todays_logs = get_todays_food_logs()
    history = get_chat_history()
    
    # Custom CSS for chat container
    st.markdown(
        """
        <style>
        .chat-assistant-container {
            background-color: rgba(6, 182, 212, 0.05);
            border-left: 3px solid #06b6d4;
            padding: 12px 18px;
            border-radius: 4px 12px 12px 4px;
            margin: 8px 0px;
        }
        .chat-user-container {
            background-color: rgba(255, 255, 255, 0.05);
            border-left: 3px solid #cbd5e1;
            padding: 12px 18px;
            border-radius: 4px 12px 12px 4px;
            margin: 8px 0px;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    # Display message history
    for msg in history:
        with st.chat_message(msg.role):
            if msg.role == "user":
                st.markdown(msg.content)
            else:
                agent_tag = f" ({msg.agent_name.capitalize()})" if msg.agent_name else ""
                st.markdown(f"**Coach{agent_tag}**\n\n{msg.content}")
            
    # Quick clear button in the sidebar or above chat
    col_chat_hdr, col_clear = st.columns([5, 1])
    with col_clear:
        if st.button("Clear Chat", help="Clear all chat history"):
            logger.info("UI Clear Chat button clicked.")
            clear_chat_history()
            st.rerun()
            
    # Chat input
    user_input = st.chat_input("Tell your coach what you ate (e.g., 'Log 100g peanut butter', 'Suggest a high-protein recipe')")
    
    if user_input:
        logger.info(f"UI Chat input submitted: '{user_input}'")
        # Render user message instantly
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Save user message
        save_chat_message(ChatMessage(role="user", content=user_input))
        
        # Call Supervisor to orchestrate and reply
        with st.spinner("Coach is thinking..."):
            history_dicts = [{"role": msg.role, "content": msg.content} for msg in get_chat_history()[:-1]]
            logger.info("Invoking SupervisorAgent router for chat processing.")
            response = supervisor_agent.route_and_process(user_input, profile, todays_logs, history_dicts)
            
            # Save coach message
            logger.info("SupervisorAgent response received. Saving to chat history.")
            save_chat_message(ChatMessage(role="assistant", content=response))
            
        logger.info("Chat input execution finished. Rerunning view.")
        st.rerun()

def render_profile(profile: UserProfile):
    """Renders user profile edit tab."""
    logger.info("Rendering User Profile & Settings tab.")
    st.markdown("<h2 class='gradient-text'>👤 User Profile & Settings</h2>", unsafe_allow_html=True)
    st.markdown("<p class='sub-text'>Review and update your physical metrics and goals below.</p>", unsafe_allow_html=True)
    
    with st.form("edit_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=12, max_value=100, value=profile.age, step=1)
            gender = st.selectbox("Gender", ["Female", "Male", "Other"], index=["female", "male", "other"].index(profile.gender.lower()))
            height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=profile.height, step=0.5)
            weight = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=profile.weight, step=0.5)
            
        with col2:
            activity = st.selectbox(
                "Activity Level",
                ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extra Active"],
                index=["sedentary", "lightly active", "moderately active", "very active", "extra active"].index(profile.activity_level.lower())
            )
            diet_type = st.selectbox(
                "Diet Type / Preferences",
                ["Standard/Anything", "Vegetarian", "Vegan", "Keto", "Paleo", "Mediterranean", "Low-Carb"],
                index=["standard/anything", "vegetarian", "vegan", "keto", "paleo", "mediterranean", "low-carb"].index(profile.diet_type.lower()) if profile.diet_type.lower() in ["standard/anything", "vegetarian", "vegan", "keto", "paleo", "mediterranean", "low-carb"] else 0
            )
            allergies = st.text_input("Allergies or Dietary Restrictions", value=profile.allergies)
            goal = st.selectbox(
                "Fitness & Health Goal",
                ["Lose Weight", "Maintain Weight", "Build Muscle", "Improve General Health"],
                index=["lose weight", "maintain weight", "build muscle", "improve general health"].index(profile.goal.lower())
            )
            
        update = st.form_submit_button("Update Profile & Recalculate Plan")
        
        if update:
            logger.info(f"UI Profile update form submitted. New values: Age={age}, Gender={gender}, Height={height}cm, Weight={weight}kg, Activity={activity}, Diet={diet_type}, Goal={goal}")
            profile.age = age
            profile.gender = gender
            profile.height = height
            profile.weight = weight
            profile.activity_level = activity
            profile.diet_type = diet_type
            profile.allergies = allergies
            profile.goal = goal
            
            with st.spinner("Recalculating plan..."):
                logger.info("Recalculating targets during profile update.")
                baselines = planner_agent.calculate_baselines(profile)
                profile.target_calories = baselines["target_calories"]
                profile.target_protein = baselines["protein_g"]
                profile.target_carbs = baselines["carbs_g"]
                profile.target_fat = baselines["fat_g"]
                
                logger.info("Saving updated user profile to database.")
                save_user_profile(profile)
                
                # Save log message to chat
                logger.info("Generating new plan explanation LLM response for chat update.")
                explanation = planner_agent.generate_plan_explanation(profile, baselines)
                save_chat_message(ChatMessage(role="assistant", content=f"🔄 I have updated your profile and recalculated your nutritional plan:\n\n{explanation}"))
                
            st.success("Profile Updated and targets recalculated!")
            st.rerun()

def render_meal_planner(profile: UserProfile):
    """Renders the dedicated Meal Planner interface."""
    logger.info("Rendering Meal Planner tab.")
    st.markdown("<h2 class='gradient-text'>📅 AI Meal Planner</h2>", unsafe_allow_html=True)
    st.markdown("<p class='sub-text'>Generate and view structured weekly or monthly meal plans tailored to your fitness targets, diet type, and restrictions.</p>", unsafe_allow_html=True)
    
    # Check if a plan already exists in database
    current_plan = get_current_meal_plan()
    
    # Selection panel inside a native Streamlit container
    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            duration = st.selectbox(
                "Select Meal Plan Duration",
                ["7-Day Weekly Plan", "4-Week Monthly Plan"],
                key="plan_duration_selection"
            )
        with col2:
            st.write("") # spacing
            st.write("")
            # We parse the duration to "week" or "month"
            dur_code = "week" if "7-Day" in duration else "month"
            generate_btn = st.button("✨ Generate My Meal Plan", use_container_width=True)
    
    if generate_btn:
        with st.spinner(f"Generating your personalized {duration}..."):
            plan_text = planner_agent.generate_meal_plan(profile, dur_code)
            current_plan = save_meal_plan(plan_text, dur_code)
            st.success("Meal plan successfully generated!")
            st.rerun()
            
    if current_plan:
        st.markdown("---")
        plan_type = "Weekly" if current_plan.duration == "week" else "Monthly"
        st.markdown(f"### Current {plan_type} Meal Plan")
        st.caption(f"Generated at: {current_plan.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Display plan in a container
        with st.container(border=True):
            st.markdown(current_plan.plan_text)
    else:
        st.info("No meal plan generated yet. Select a duration above and click 'Generate My Meal Plan' to create one!")

