import streamlit as st
import pandas as pd
import json
import re
import ast  
from io import BytesIO

st.set_page_config(page_title="MotionX Dialogue & SFX Merger", layout="wide")

def classify_text(text):
    """Categorizes text as SFX if all words are uppercase, else Dialogue."""
    if pd.isna(text) or str(text).strip() == "":
        return None
    tokens = re.findall(r'\b\w+\b', str(text))
    if not tokens:
        return "dialogues"
    if all(t.isupper() for t in tokens):
        return "sfx"
    return "dialogues"

def check_panel_has_audio(prompt_val):
    """
    Parses the prompt to find audio content.
    Handles 'prompt' prefix, single quotes, and None values.
    """
    if pd.isna(prompt_val) or str(prompt_val).strip() in ["", "nan", "None"]:
        return False
    
    try:
        clean_val = str(prompt_val).strip()
        if clean_val.startswith('prompt'):
            clean_val = clean_val[6:].strip()

        try:
            data = ast.literal_eval(clean_val)
        except (ValueError, SyntaxError):
            data = json.loads(clean_val)
        
        if not isinstance(data, dict):
            return False

        cuts = data.get('cuts', [])
        for cut in cuts:
            audio = cut.get('audio')
            if isinstance(audio, dict):
                has_dialogue = any(str(v).strip() for v in audio.get('dialogue', {}).values() if v)
                has_thought = any(str(v).strip() for v in audio.get('thought', {}).values() if v)
                has_narration = audio.get('narration') is not None and str(audio.get('narration')).strip() != ""
                
                if has_dialogue or has_thought or has_narration:
                    return True
        return False
    except:
        return False

st.title("📖 MotionX Dialogue & SFX Merger")

# --- FILE UPLOADS ---
col1, col2 = st.columns(2)
with col1:
    main_file = st.file_uploader("Upload Main Excel Sheet", type=['xlsx'])
with col2:
    dialog_file = st.file_uploader("Upload Dialogue Excel Sheet", type=['xlsx'])

if main_file and dialog_file:
    df_main = pd.read_excel(main_file)
    df_dialog = pd.read_excel(dialog_file)

    st.success("Files uploaded successfully!")

    # --- DYNAMIC IMAGE NUMBER GENERATION ---
    st.info("🔍 Auditing Main Sheet prompts for audio content...")
    
    audio_counter = 1
    new_image_numbers = []
    
    for idx, row in df_main.iterrows():
        if 'prompt' in df_main.columns and check_panel_has_audio(row['prompt']):
            new_image_numbers.append(audio_counter)
            audio_counter += 1
        else:
            new_image_numbers.append("-")
            
    df_main['image_number'] = new_image_numbers

    # --- DATA ANALYSIS ---
    episodes = df_dialog['episode_number'].unique()
    selected_ep = st.selectbox("Select Episode to Merge", sorted(episodes))
    
    ep_dialog = df_dialog[df_dialog['episode_number'] == selected_ep]
    if not ep_dialog.empty:
        min_p = int(ep_dialog['image_number'].min())
        max_p = int(ep_dialog['image_number'].max())

        st.write(f"**Episode {selected_ep} Summary:**")
        st.write(f"- Dialogue Sheet Panels: {min_p} to {max_p}")
        st.write(f"- Active Panels found in Main Sheet: {audio_counter - 1}")

        range_col1, range_col2 = st.columns(2)
        with range_col1:
            start_p = st.number_input("Start Image Number", value=min_p, min_value=min_p, max_value=max_p)
        with range_col2:
            end_p = st.number_input("End Image Number", value=max_p, min_value=min_p, max_value=max_p)

        if st.button("Generate Merged Sheet"):
            # 1. Create JSON map from Dialogue Sheet
            mask = (df_dialog['episode_number'] == selected_ep) & \
                   (df_dialog['image_number'] >= start_p) & \
                   (df_dialog['image_number'] <= end_p)
            df_filtered = df_dialog[mask].copy()

            json_map = {}
            for img_num, group in df_filtered.groupby('image_number'):
                panel_obj = {"dialogues": {}, "sfx": {}}
                for _, row in group.iterrows():
                    d_id = str(row['dialogue_number'])
                    txt = row['QC Dialogues'] if pd.notna(row['QC Dialogues']) else row['adapted_dialogue']
                    category = classify_text(txt)
                    if category:
                        panel_obj[category][d_id] = str(txt).strip()
                
                json_map[int(img_num)] = json.dumps(panel_obj, ensure_ascii=False)

            # 2. Map JSON strings to Main Sheet
            def apply_json(row):
                try:
                    val = row['image_number']
                    if val != "-" and int(val) in json_map:
                        return json_map[int(val)]
                except:
                    pass
                return None

            df_main['dialogue_tab'] = df_main.apply(apply_json, axis=1)

            # --- COLUMN FILTERING ---
            # Define the final requested columns and order
            final_columns = [
                'episode_number', 
                'panel_number', 
                'image_number', 
                'dialogue', 
                'dialogue_tab', 
                'prompt', 
                '_processed_prompt'
            ]
            
            # Filter the dataframe to only include existing requested columns
            # (In case _processed_prompt is missing in some files)
            existing_final_columns = [col for col in final_columns if col in df_main.columns]
            df_export = df_main[existing_final_columns].copy()

            st.write("### Preview (Final Column Order)")
            st.dataframe(df_export[df_export['image_number'] != "-"].head(15))

            # --- EXPORT ---
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Merged Excel",
                data=output.getvalue(),
                file_name=f"MotionX_Final_Ep{selected_ep}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning(f"No data found for Episode {selected_ep} in the Dialogue Sheet.")