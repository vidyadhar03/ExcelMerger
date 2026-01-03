import streamlit as st
from cleanMain import render_main_cleaner
from cleanDialogue import render_dialogue_cleaner
from merger import render_merger

st.set_page_config(page_title="MotionX Automation Tool", layout="wide")

# 1. Initialize Session State for Navigation
if 'current_step' not in st.session_state:
    st.session_state['current_step'] = "1. Clean Main Sheet"

st.title("🎬 MotionX Automation Dashboard")

# 2. Navigation Bar
# IMPORTANT: 'key="current_step"' binds this widget directly to the session state.
# - If you click the radio button, it updates the state.
# - If code (like the 'Next' button) updates the state, this radio button updates visually.
steps = ["1. Clean Main Sheet", "2. Clean Dialogue Sheet", "3. Merge & Validate"]

st.radio(
    "Navigate to:", 
    steps, 
    horizontal=True, 
    label_visibility="collapsed",
    key="current_step"
)

st.divider()

# 3. Render Active Step
# We check the state variable to decide which module to load
if st.session_state['current_step'] == "1. Clean Main Sheet":
    render_main_cleaner()
    
elif st.session_state['current_step'] == "2. Clean Dialogue Sheet":
    render_dialogue_cleaner()
    
elif st.session_state['current_step'] == "3. Merge & Validate":
    render_merger()