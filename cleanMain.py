import streamlit as st
import pandas as pd
import json
import ast
from io import BytesIO

st.set_page_config(page_title="Step 1: Clean Main Sheet", layout="wide")

def count_dialogues_in_prompt(prompt_val):
    """
    Parses the prompt JSON and counts distinct dialogue lines.
    RULES:
    1. Look inside ['cuts'] -> ['audio'] -> ['dialogue']
    2. Count the number of keys (speakers) in the dialogue dictionary.
    3. IGNORE ['thought'] and ['narration'].
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
                    # Count how many speaker keys exist (e.g., Accomplice + Morgan = 2)
                    total_count += len(dialogue_dict)
                    
        return total_count

    except Exception:
        # If parsing fails, return 0
        return 0

st.title("🧹 Step 1: Main Sheet Cleaner")
st.markdown("Upload the **Main Excel Sheet**. Select the Episode and Panel range to generate a clean task file.")

uploaded_file = st.file_uploader("Upload Main Excel", type=['xlsx'])

if uploaded_file:
    # 1. Read Excel File (Load all sheets to get names)
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        st.success(f"File uploaded! Found {len(sheet_names)} sheets (Episodes).")
        
        # --- UI: EPISODE SELECTION ---
        st.markdown("---")
        st.subheader("1. Select Episode")
        selected_sheet = st.selectbox("Choose the Episode (Sheet) to process:", sheet_names)

        if selected_sheet:
            # Load specific sheet data
            df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
            
            # Ensure panel_number exists
            if 'panel_number' not in df.columns:
                st.error(f"❌ Column 'panel_number' not found in sheet '{selected_sheet}'")
            else:
                # Get Min/Max Panels
                min_panel = int(df['panel_number'].min())
                max_panel = int(df['panel_number'].max())
                total_panels = len(df)

                st.info(f"**{selected_sheet} Summary:** Found {total_panels} rows. Panels range from {min_panel} to {max_panel}.")

                # --- UI: PANEL RANGE SELECTION ---
                st.subheader("2. Select Panel Range")
                col1, col2 = st.columns(2)
                
                with col1:
                    start_p = st.number_input("Start Panel Number", value=min_panel, min_value=min_panel, max_value=max_panel)
                with col2:
                    end_p = st.number_input("End Panel Number", value=max_panel, min_value=min_panel, max_value=max_panel)

                # --- PROCESSING ---
                st.markdown("---")
                if st.button("🚀 Clean & Generate Task File"):
                    if start_p > end_p:
                        st.error("Error: Start Panel cannot be greater than End Panel.")
                    else:
                        with st.spinner("Processing selected range..."):
                            
                            # A. Filter Dataframe by Range
                            mask = (df['panel_number'] >= start_p) & (df['panel_number'] <= end_p)
                            df_filtered = df[mask].copy()

                            if df_filtered.empty:
                                st.warning("No rows found in this panel range.")
                            else:
                                # B. Calculate counts (Only for filtered rows)
                                df_filtered['temp_count'] = df_filtered['prompt'].apply(count_dialogues_in_prompt)

                                # C. Generate Ranges (Cumulative Sum restarts for this batch)
                                df_filtered['cumsum'] = df_filtered['temp_count'].cumsum()
                                df_filtered['prev_cumsum'] = df_filtered['cumsum'].shift(1).fillna(0).astype(int)
                                
                                def format_range(row):
                                    count = row['temp_count']
                                    if count == 0:
                                        return "0-0"
                                    start = row['prev_cumsum'] + 1
                                    end = row['cumsum']
                                    return f"{start}-{end}"

                                df_filtered['dialogue_range'] = df_filtered.apply(format_range, axis=1)

                                # D. Filter Columns
                                required_columns = ['episode_number', 'panel_number', 'prompt', 'dialogue_range']
                                missing_cols = [col for col in required_columns if col not in df_filtered.columns]
                                
                                if missing_cols:
                                    st.error(f"❌ Missing columns: {missing_cols}")
                                else:
                                    df_clean = df_filtered[required_columns].copy()

                                    # E. Preview
                                    st.subheader("Preview Result")
                                    st.dataframe(df_clean.head(10))
                                    
                                    total_dialogues = df_filtered['temp_count'].sum()
                                    st.success(f"✅ Processed Panels {start_p} to {end_p}. Total Dialogues: {total_dialogues}")

                                    # F. Download
                                    output = BytesIO()
                                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                        df_clean.to_excel(writer, index=False)
                                    
                                    clean_filename = f"Cleaned_{selected_sheet}_Panels_{start_p}-{end_p}.xlsx"
                                    
                                    st.download_button(
                                        label="📥 Download Cleaned Sheet",
                                        data=output.getvalue(),
                                        file_name=clean_filename,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )

    except Exception as e:
        st.error(f"Error reading file: {e}")