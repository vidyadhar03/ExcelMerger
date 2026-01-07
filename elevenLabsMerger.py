import streamlit as st
import pandas as pd
import json
import ast
from io import BytesIO

def extract_panel_metadata(row):
    """
    Parses the 'prompt' JSON from the Main Sheet to extract:
    - action_description
    - characters_included
    - panel_duration
    """
    prompt_val = row['prompt']
    
    # Defaults
    actions = []
    characters = set()
    duration = 0

    try:
        # 1. Parse JSON
        if pd.isna(prompt_val):
            return pd.Series(["", "[]", 0])
            
        clean_val = str(prompt_val).strip()
        if clean_val.startswith('prompt'): 
            clean_val = clean_val[6:].strip()
            
        try: 
            p_data = ast.literal_eval(clean_val)
        except: 
            p_data = json.loads(clean_val)
            
        if not isinstance(p_data, dict):
            return pd.Series(["", "[]", 0])

        # 2. Extract Data
        duration = p_data.get('duration', 0)
        
        cuts = p_data.get('cuts', [])
        for cut in cuts:
            # Actions
            act = cut.get('action')
            if act:
                actions.append(str(act))
            
            # Characters (from audio > dialogue keys)
            audio = cut.get('audio', {})
            if isinstance(audio, dict):
                dial = audio.get('dialogue', {})
                if isinstance(dial, dict):
                    for speaker in dial.keys():
                        characters.add(speaker)

    except Exception:
        pass # Return defaults on error

    # Format Outputs
    action_str = " | ".join(actions)
    chars_json = json.dumps(list(characters), ensure_ascii=False)
    
    return pd.Series([action_str, chars_json, duration])

def render_eleven_labs_merger():
    st.header("4️⃣ Dialogue Merger (ElevenLabs)")
    st.markdown("Generates a flat list of dialogues enriched with Panel Metadata for Audio Generation.")

    # --- INPUT HANDLER ---
    df_main = None
    df_dial = None

    # Load Main Sheet (Source of Metadata)
    if 'clean_main_df' in st.session_state:
        st.info("✅ Main Sheet loaded from Step 1 (Metadata Source).")
        df_main = st.session_state['clean_main_df'].copy()
    else:
        clean_main_file = st.file_uploader("Upload Cleaned Main Sheet", type=['xlsx'], key="el_main")
        if clean_main_file: df_main = pd.read_excel(clean_main_file)

    # Load Dialogue Sheet (Source of Rows)
    if 'clean_dialog_df' in st.session_state:
        st.info("✅ Dialogue Sheet loaded from Step 2 (Dialogue Source).")
        df_dial = st.session_state['clean_dialog_df'].copy()
    else:
        clean_dialog_file = st.file_uploader("Upload Cleaned Dialogue Sheet", type=['xlsx'], key="el_dialog")
        if clean_dialog_file: df_dial = pd.read_excel(clean_dialog_file)

    # --- PROCESSING LOGIC ---
    if df_main is not None and df_dial is not None:
        st.divider()
        
        # Validation Check
        if 'image_number' not in df_dial.columns:
            st.error("❌ 'image_number' column missing in Dialogue Sheet. Cannot map to panels.")
            return
            
        if st.button("🎧 Generate Audio Script", type="primary"):
            with st.spinner("Extracting metadata and mapping to dialogues..."):
                
                # 1. Prepare Metadata Lookup Table (from Main Sheet)
                # We apply extraction logic to every panel first
                metadata_cols = ['panel_action_description', 'panel_characters_included', 'panel_duration']
                
                # Create a temporary dataframe for metadata
                df_meta = df_main[['panel_number', 'prompt']].copy()
                df_meta[metadata_cols] = df_meta.apply(extract_panel_metadata, axis=1)
                
                # Drop raw prompt, keep only clean metadata
                df_meta_clean = df_meta[['panel_number'] + metadata_cols]

                # 2. Merge Logic (Left Join)
                # We keep every dialogue row, and attach matching panel info
                df_merged = pd.merge(
                    df_dial, 
                    df_meta_clean, 
                    left_on='image_number', 
                    right_on='panel_number', 
                    how='left'
                )

                # 3. Clean & Rename Columns
                # We rename Step 2 columns to match your requirement
                # final_dialogue_text -> dialogue
                
                final_columns_map = {
                    'episode_number': 'episode_number',
                    'image_number': 'panel_number', # Rename image_number to panel_number
                    'final_dialogue_text': 'dialogue',
                    'panel_action_description': 'panel_action_description',
                    'panel_characters_included': 'panel_characters_included',
                    'panel_duration': 'panel_duration'
                }

                # Filter and Rename
                # Ensure all source columns exist
                available_cols = [c for c in final_columns_map.keys() if c in df_merged.columns]
                df_final = df_merged[available_cols].rename(columns=final_columns_map)

                # Fill NaN for missing lookups (in case a panel # doesn't exist in main sheet)
                df_final['panel_action_description'] = df_final['panel_action_description'].fillna("")
                df_final['panel_characters_included'] = df_final['panel_characters_included'].fillna("[]")
                df_final['panel_duration'] = df_final['panel_duration'].fillna(0)

                st.success(f"✅ Generated {len(df_final)} audio lines with context!")

                # 4. Preview
                st.write("### Preview")
                st.dataframe(df_final.head())

                # 5. Download
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False)
                
                fname = "MotionX_ElevenLabs_Audio_Script.xlsx"
                
                st.download_button(
                    label="📥 Download Audio Script", 
                    data=output.getvalue(), 
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )