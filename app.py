import streamlit as st
from src.database import init_db, get_user_profile, get_todays_food_logs
from src.views import render_onboarding, render_dashboard, render_coach, render_profile, load_css, render_meal_planner

# Set Page Config
st.set_page_config(
    page_title="AI Nutrition Coach",
    page_icon="🥑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database on Startup
init_db()

# Load Custom Styles
load_css()

# Retrieve Profile
profile = get_user_profile()

if not profile:
    # Force onboarding flow
    render_onboarding()
else:
    # Render Sidebar info
    st.sidebar.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;">🥑</span>
            <h3 style="margin-top: 5px; margin-bottom: 0px;">Coach AI</h3>
            <p style="color: #94a3b8; font-size: 0.9rem;">Your Personalized Nutrition Assistant</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.sidebar.markdown("### Profile Summary")
    st.sidebar.markdown(f"**Goal:** {profile.goal}")
    st.sidebar.markdown(f"**Diet:** {profile.diet_type}")
    st.sidebar.markdown(f"**Weight:** {profile.weight} kg")
    st.sidebar.markdown(f"**Height:** {profile.height} cm")
    if profile.allergies and profile.allergies.lower() != "none":
        st.sidebar.markdown(f"**Allergies:** ⚠️ {profile.allergies}")
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Daily Budget")
    st.sidebar.markdown(f"- Calories: **{profile.target_calories or 0:.0f} kcal**")
    st.sidebar.markdown(f"- Protein: **{profile.target_protein or 0:.0f}g**")
    st.sidebar.markdown(f"- Carbs: **{profile.target_carbs or 0:.0f}g**")
    st.sidebar.markdown(f"- Fats: **{profile.target_fat or 0:.0f}g**")
    
    # Calculate simple progress indicators for sidebar
    todays_logs = get_todays_food_logs()
    c_cal = sum(l.calories for l in todays_logs)
    c_prot = sum(l.protein for l in todays_logs)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Today's Status")
    st.sidebar.progress(min(c_cal / profile.target_calories, 1.0) if profile.target_calories else 0.0)
    st.sidebar.write(f"Calories: {c_cal:.0f} / {profile.target_calories or 0:.0f} kcal")
    
    # Main Navigation Tabs
    tab_dash, tab_plan, tab_coach, tab_prof = st.tabs([
        "📊 Dashboard", 
        "📅 Meal Planner",
        "💬 AI Coach Chat", 
        "👤 My Profile"
    ])
    
    with tab_dash:
        render_dashboard(profile)
        
    with tab_plan:
        render_meal_planner(profile)
        
    with tab_coach:
        render_coach(profile)
        
    with tab_prof:
        render_profile(profile)

# Force watcher reload 5
