import streamlit as st
from cleanMain import render_main_cleaner
from cleanDialogue import render_dialogue_cleaner
from merger import render_merger

st.set_page_config(page_title="MotionX Automation Tool", layout="wide")

if 'selected_episode_num' not in st.session_state:
    st.session_state.selected_episode_num = None

st.title("🎬 MotionX Automation Dashboard")

# Create Tabs for a cleaner UI
tab1, tab2, tab3 = st.tabs(["1. Clean Main Sheet", "2. Clean Dialogue Sheet", "3. Merge & Validate"])

with tab1:
    render_main_cleaner()

with tab2:
    render_dialogue_cleaner()

with tab3:
    render_merger()