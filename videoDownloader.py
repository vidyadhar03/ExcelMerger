import streamlit as st
import pandas as pd
import requests
import zipfile
import io

def render_video_downloader():
    st.header("🎥 1.5 Video Asset Downloader")
    
    # Check if cleaned data exists from Step 1
    if 'clean_main_df' not in st.session_state:
        st.warning("⚠️ Please complete 'Step 1: Clean Main Sheet' first.")
        return

    df = st.session_state['clean_main_df']
    
    # User selection for panels
    all_panels = df['panel_number'].unique().tolist()
    selected_panels = st.multiselect(
        "Select Panels to Download Videos for:",
        options=all_panels,
        default=all_panels
    )

    if st.button("Generate Video ZIP", type="primary"):
        if not selected_panels:
            st.error("Select at least one panel.")
            return
            
        filtered_df = df[df['panel_number'].isin(selected_panels)]
        
        zip_buffer = io.BytesIO()
        progress_bar = st.progress(0)
        status_text = st.empty()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, (idx, row) in enumerate(filtered_df.iterrows()):
                url = row.get('video_url') # Ensure your Step 1 keeps the video_url column
                if pd.isna(url) or not str(url).startswith("http"):
                    continue
                
                # Naming convention
                ep = row.get('episode_number', 'X')
                pnl = row.get('panel_number', 'Y')
                file_name = f"Episode{ep}_Panel{pnl}.mp4"
                
                status_text.text(f"Downloading {file_name}...")
                
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        zip_file.writestr(file_name, response.content)
                except Exception as e:
                    st.error(f"Failed to download panel {pnl}: {e}")
                
                progress_bar.progress((i + 1) / len(filtered_df))

        status_text.text("✅ ZIP created successfully!")
        
        st.download_button(
            label="📥 Download All Videos (ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"Videos_{st.session_state.get('main_filename_suffix', 'export')}.zip",
            mime="application/zip"
        )