import streamlit as st
import pandas as pd
import json
import ast
import re
from io import BytesIO

def count_dialogues_in_prompt(prompt_val):
    if pd.isna(prompt_val) or str(prompt_val).strip() in ["", "nan", "None"]:
        return 0
    try:
        clean_val = str(prompt_val).strip()
        if clean_val.startswith('prompt'): clean_val = clean_val[6:].strip()
        try: data = ast.literal_eval(clean_val)
        except: data = json.loads(clean_val)
        
        if not isinstance(data, dict): return 0

        total_count = 0
        for cut in data.get('cuts', []):
            audio = cut.get('audio', {})
            if isinstance(audio, dict):
                total_count += len(audio.get('dialogue', {}))
        return total_count
    except: return 0

def render_main_cleaner():
    st.header("1️⃣ Main Sheet Cleaner")
    st.markdown("Generates Global IDs for panels in the Main Excel.")

    main_file = st.file_uploader("Upload Main Excel (Raw)", type=['xlsx'], key="main_uploader")

    if main_file:
        try:
            xls_main = pd.ExcelFile(main_file)
            main_sheet_name = st.selectbox("Select Episode (Sheet)", xls_main.sheet_names, key="main_sheet_select")
            
            # Auto-detect episode number
            try:
                ep_num = int(re.search(r'\d+', main_sheet_name).group())
                st.session_state.selected_episode_num = ep_num
            except: pass

            df_main = pd.read_excel(main_file, sheet_name=main_sheet_name)
            
            if 'panel_number' in df_main.columns:
                min_p, max_p = int(df_main['panel_number'].min()), int(df_main['panel_number'].max())
                
                c1, c2 = st.columns(2)
                start_p = c1.number_input("Start Panel", value=min_p, min_value=min_p, max_value=max_p)
                end_p = c2.number_input("End Panel", value=max_p, min_value=min_p, max_value=max_p)

                if st.button("Clean & Process Main Sheet", type="primary"):
                    # 1. Global Calculation
                    df_main['temp_count'] = df_main['prompt'].apply(count_dialogues_in_prompt)
                    df_main['cumsum'] = df_main['temp_count'].cumsum()
                    df_main['prev_cumsum'] = df_main['cumsum'].shift(1).fillna(0).astype(int)
                    
                    df_main['dialogue_range'] = df_main.apply(
                        lambda r: "0-0" if r['temp_count'] == 0 else f"{r['prev_cumsum'] + 1}-{r['cumsum']}", axis=1
                    )

                    # 2. Filter & Select Cols
                    mask = (df_main['panel_number'] >= start_p) & (df_main['panel_number'] <= end_p)
                    df_main_clean = df_main[mask].copy()
                    
                    cols = ['episode_number', 'panel_number', 'prompt', 'dialogue_range']
                    final_cols = [c for c in cols if c in df_main_clean.columns]
                    df_export_main = df_main_clean[final_cols]

                    # 3. SAVE TO SESSION STATE
                    st.session_state['clean_main_df'] = df_export_main
                    st.success("✅ Main Sheet processed and stored in memory! You can now proceed to Step 3 (or download below).")

                    # 4. Download Option
                    output_main = BytesIO()
                    with pd.ExcelWriter(output_main, engine='openpyxl') as writer:
                        df_export_main.to_excel(writer, index=False)
                    
                    st.download_button("📥 Download Cleaned Main Sheet", data=output_main.getvalue(),
                                       file_name=f"Cleaned_Main_{main_sheet_name}_P{start_p}-{end_p}.xlsx")
            else:
                st.error("Column 'panel_number' missing.")
        except Exception as e:
            st.error(f"Error: {e}")