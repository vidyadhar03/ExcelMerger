import streamlit as st
import pandas as pd
import json
import ast
import re
from io import BytesIO

def extract_dialogue_content(prompt_val):
    """
    Parses the prompt and returns a JSON string of all dialogues in order.
    Format: [{"speaker": "X", "text": "Y"}, ...]
    """
    if pd.isna(prompt_val) or str(prompt_val).strip() in ["", "nan", "None"]:
        return "[]"

    try:
        clean_val = str(prompt_val).strip()
        if clean_val.startswith('prompt'):
            clean_val = clean_val[6:].strip()
            
        try:
            data = ast.literal_eval(clean_val)
        except (ValueError, SyntaxError):
            data = json.loads(clean_val)
        
        if not isinstance(data, dict):
            return "[]"

        dialogue_list = []
        cuts = data.get('cuts', [])
        
        for cut in cuts:
            audio = cut.get('audio', {})
            if isinstance(audio, dict):
                dialogue_dict = audio.get('dialogue', {})
                if isinstance(dialogue_dict, dict):
                    for speaker, text in dialogue_dict.items():
                        entry = {
                            "speaker": str(speaker).strip(),
                            "text": str(text).strip()
                        }
                        dialogue_list.append(entry)
                    
        return json.dumps(dialogue_list)

    except Exception:
        return "[]"

def render_main_cleaner():
    st.header("1️⃣ Main Sheet Cleaner")
    st.markdown("Generates Global IDs and extracts clean dialogue content from the Main Excel.")

    main_file = st.file_uploader("Upload Main Excel (Raw)", type=['xlsx'], key="main_uploader")

    if main_file:
        try:
            xls_main = pd.ExcelFile(main_file)
            main_sheets = xls_main.sheet_names
            
            # Sheet Selection
            main_sheet_name = st.selectbox("Select Episode (Sheet)", main_sheets, key="main_sheet_select")
            
            # Heuristic: Try to extract episode number
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
                # --- NEW: Column Selection Area ---
                st.divider()
                st.subheader("⚙️ Output Configuration")
                
                # 1. Get all available columns from the raw file
                all_columns = df_main.columns.tolist()
                
                # 2. Define defaults (The ones we definitely usually need)
                default_cols = [c for c in ['episode_number', 'panel_number', 'prompt'] if c in all_columns]
                
                col_conf1, col_conf2 = st.columns([2, 1])
                
                with col_conf1:
                    # 3. Allow user to select/deselect columns
                    selected_raw_cols = st.multiselect(
                        "Select columns to keep from original file:",
                        options=all_columns,
                        default=default_cols,
                        help="The new 'dialogue_range' and 'dialogue_content' columns will be added automatically."
                    )
                
                # Panel Range Inputs
                with col_conf2:
                    min_p = int(df_main['panel_number'].min())
                    max_p = int(df_main['panel_number'].max())
                    start_p = st.number_input("Start Panel", value=min_p, min_value=min_p, max_value=max_p)
                    end_p = st.number_input("End Panel", value=max_p, min_value=min_p, max_value=max_p)

                st.divider()

                if st.button("Clean & Process Main Sheet", type="primary"):
                    with st.spinner("Extracting Dialogues & Calculating Global Ranges..."):
                        
                        # 1. Extract Content
                        df_main['dialogue_content'] = df_main['prompt'].apply(extract_dialogue_content)

                        # 2. Global Calculation
                        df_main['temp_count'] = df_main['dialogue_content'].apply(lambda x: len(json.loads(x)))
                        df_main['cumsum'] = df_main['temp_count'].cumsum()
                        df_main['prev_cumsum'] = df_main['cumsum'].shift(1).fillna(0).astype(int)
                        
                        def format_range(row):
                            if row['temp_count'] == 0:
                                return "0-0"
                            return f"{row['prev_cumsum'] + 1}-{row['cumsum']}"

                        df_main['dialogue_range'] = df_main.apply(format_range, axis=1)

                        # 3. Filter by Panel Range
                        mask = (df_main['panel_number'] >= start_p) & (df_main['panel_number'] <= end_p)
                        df_main_clean = df_main[mask].copy()
                        
                        # 4. Construct Final Columns (User Selected + Generated)
                        # We force the addition of the 2 new calculated columns
                        generated_cols = ['dialogue_range', 'dialogue_content']
                        
                        # Combine lists, avoiding duplicates if user somehow selected a column name that matches our generated ones
                        final_export_cols = [c for c in selected_raw_cols if c not in generated_cols] + generated_cols
                        
                        df_export_main = df_main_clean[final_export_cols]

                        # 5. Save to Session State
                        st.session_state['clean_main_df'] = df_export_main
                        st.session_state['main_filename_suffix'] = f"{ep_num_str}_Panels_{start_p}-{end_p}"

                        st.success("✅ Main Sheet processed and stored in memory!")

                        # --- DOWNLOAD AREA ---
                        col_d, col_next = st.columns([1, 1])
                        
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
                        
                        if col_next.button("👉 Go to Step 2 (Clean Dialogues)"):
                            st.session_state['current_step'] = "2. Clean Dialogue Sheet"
                            st.rerun()

            else:
                st.error("❌ Column 'panel_number' not found in this sheet.")

        except Exception as e:
            st.error(f"Error processing file: {e}")