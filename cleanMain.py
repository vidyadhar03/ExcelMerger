import streamlit as st
import pandas as pd
import json
import ast
import re
from io import BytesIO

def count_dialogues_in_prompt(prompt_val):
    """
    Parses the prompt JSON and counts distinct dialogue lines.
    Rules: Count keys in audio['dialogue']. Ignore 'thought'/'narration'.
    """
    if pd.isna(prompt_val) or str(prompt_val).strip() in ["", "nan", "None"]:
        return 0

    try:
        # Clean and parse the string to a dictionary
        clean_val = str(prompt_val).strip()
        if clean_val.startswith('prompt'):
            clean_val = clean_val[6:].strip()
            
        try:
            data = ast.literal_eval(clean_val)
        except (ValueError, SyntaxError):
            data = json.loads(clean_val)
        
        if not isinstance(data, dict):
            return 0

        total_count = 0
        cuts = data.get('cuts', [])
        
        for cut in cuts:
            audio = cut.get('audio', {})
            if isinstance(audio, dict):
                # We only access 'dialogue'. We IGNORE 'thought' and 'narration'.
                dialogue_dict = audio.get('dialogue', {})
                if isinstance(dialogue_dict, dict):
                    # Count how many speaker keys exist
                    total_count += len(dialogue_dict)
                    
        return total_count

    except Exception:
        return 0

def render_main_cleaner():
    st.header("1️⃣ Main Sheet Cleaner")
    st.markdown("Generates Global IDs for panels in the Main Excel.")

    main_file = st.file_uploader("Upload Main Excel (Raw)", type=['xlsx'], key="main_uploader")

    if main_file:
        try:
            xls_main = pd.ExcelFile(main_file)
            main_sheets = xls_main.sheet_names
            
            # Sheet Selection
            main_sheet_name = st.selectbox("Select Episode (Sheet)", main_sheets, key="main_sheet_select")
            
            # Heuristic: Try to extract episode number (e.g. "Episode 1" -> 1)
            ep_num_str = ""
            try:
                ep_match = re.search(r'\d+', main_sheet_name)
                if ep_match:
                    ep_num = int(ep_match.group())
                    st.session_state.selected_episode_num = ep_num
                    ep_num_str = f"Ep{ep_num}"
            except:
                pass

            # Load Data
            df_main = pd.read_excel(main_file, sheet_name=main_sheet_name)
            
            if 'panel_number' in df_main.columns:
                # Get Min/Max Panels
                min_p = int(df_main['panel_number'].min())
                max_p = int(df_main['panel_number'].max())
                
                c1, c2 = st.columns(2)
                start_p = c1.number_input("Start Panel", value=min_p, min_value=min_p, max_value=max_p)
                end_p = c2.number_input("End Panel", value=max_p, min_value=min_p, max_value=max_p)

                if st.button("Clean & Process Main Sheet", type="primary"):
                    with st.spinner("Calculating Global Ranges..."):
                        # 1. Global Calculation (Must happen BEFORE filtering)
                        # This ensures Panel 8 remembers the counts from Panels 1-7
                        df_main['temp_count'] = df_main['prompt'].apply(count_dialogues_in_prompt)
                        df_main['cumsum'] = df_main['temp_count'].cumsum()
                        df_main['prev_cumsum'] = df_main['cumsum'].shift(1).fillna(0).astype(int)
                        
                        def format_range(row):
                            if row['temp_count'] == 0:
                                return "0-0"
                            return f"{row['prev_cumsum'] + 1}-{row['cumsum']}"

                        df_main['dialogue_range'] = df_main.apply(format_range, axis=1)

                        # 2. Filter by Panel Range
                        mask = (df_main['panel_number'] >= start_p) & (df_main['panel_number'] <= end_p)
                        df_main_clean = df_main[mask].copy()
                        
                        # 3. Select Columns
                        required_columns = ['episode_number', 'panel_number', 'prompt', 'dialogue_range']
                        # Ensure columns exist
                        final_cols = [c for c in required_columns if c in df_main_clean.columns]
                        df_export_main = df_main_clean[final_cols]

                        # 4. Save to Session State (for the Merger Tab)
                        st.session_state['clean_main_df'] = df_export_main
                        
                        # Store suffix for Step 3 filename generation
                        st.session_state['main_filename_suffix'] = f"{ep_num_str}_Panels_{start_p}-{end_p}"

                        st.success("✅ Main Sheet processed and stored in memory!")

                        # --- ACTION AREA ---
                        st.divider()
                        col_d, col_next = st.columns([1, 1])
                        
                        # Download Button
                        output_main = BytesIO()
                        with pd.ExcelWriter(output_main, engine='openpyxl') as writer:
                            df_export_main.to_excel(writer, index=False)
                        
                        clean_filename = f"Cleaned_Main_{ep_num_str}_Panels_{start_p}-{end_p}.xlsx"
                        
                        col_d.download_button(
                            label="📥 Download Cleaned Sheet",
                            data=output_main.getvalue(),
                            file_name=clean_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        # Navigation Button
                        if col_next.button("👉 Go to Step 2 (Clean Dialogues)"):
                            st.session_state['current_step'] = "2. Clean Dialogue Sheet"
                            st.rerun()

            else:
                st.error("❌ Column 'panel_number' not found in this sheet.")

        except Exception as e:
            st.error(f"Error processing file: {e}")