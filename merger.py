import streamlit as st
import pandas as pd
import json
import ast
from io import BytesIO

def render_merger():
    st.header("3️⃣ The Final Merge")
    st.markdown("Validates data, updates the Prompt JSON with new dialogues, and extracts metadata context for OpenAI.")

    # --- INPUT HANDLER ---
    df_main = None
    df_dial = None

    # Load Main Sheet from Memory or Upload
    if 'clean_main_df' in st.session_state:
        st.info("✅ Main Sheet loaded from Step 1.")
        df_main = st.session_state['clean_main_df'].copy()
    else:
        clean_main_file = st.file_uploader("Upload Cleaned Main Sheet", type=['xlsx'], key="merge_main")
        if clean_main_file: df_main = pd.read_excel(clean_main_file)

    # Load Dialogue Sheet from Memory or Upload
    if 'clean_dialog_df' in st.session_state:
        st.info("✅ Dialogue Sheet loaded from Step 2.")
        df_dial = st.session_state['clean_dialog_df'].copy()
    else:
        clean_dialog_file = st.file_uploader("Upload Cleaned Dialogue Sheet", type=['xlsx'], key="merge_dialog")
        if clean_dialog_file: df_dial = pd.read_excel(clean_dialog_file)

    # --- MAIN LOGIC ---
    if df_main is not None and df_dial is not None:
        st.divider()
        st.subheader("Validation")

        try:
            # 1. Validation: Match IDs between sheets
            valid_ranges = df_main[df_main['dialogue_range'] != "0-0"]
            
            if valid_ranges.empty:
                st.warning("⚠️ No dialogues found in the Main Sheet range.")
                start_id, end_id, count_req, count_found = 0, 0, 0, 0
            else:
                start_id = int(valid_ranges.iloc[0]['dialogue_range'].split('-')[0])
                end_id = int(valid_ranges.iloc[-1]['dialogue_range'].split('-')[1])
                
                # Filter Dialogues to match the requested range
                df_dial_filtered = df_dial[
                    (df_dial['global_dialogue_id'] >= start_id) & 
                    (df_dial['global_dialogue_id'] <= end_id)
                ]
                
                count_req = end_id - start_id + 1
                count_found = len(df_dial_filtered)
            
            # Display Stats
            c1, c2 = st.columns(2)
            c1.metric("Required IDs (Main Sheet)", f"{start_id} - {end_id}")
            c2.metric("Available Dialogues (Step 2)", count_found, delta=count_found - count_req)

            if count_found == count_req:
                if count_req > 0:
                    st.success("✅ VALIDATION SUCCESSFUL")
                
                if st.button("🚀 Process, Update Prompts & Merge", type="primary"):
                    
                    # 2. Create Lookup Map for fast text retrieval
                    if count_req > 0:
                        dialogue_map = pd.Series(
                            df_dial_filtered.final_dialogue_text.values,
                            index=df_dial_filtered.global_dialogue_id
                        ).to_dict()
                    else:
                        dialogue_map = {}

                    # 3. Define the Master Processing Function
                    # This runs on every row to update the prompt AND extract columns simultaneously
                    def process_panel(row):
                        # A. Parse the Prompt String into a Dictionary
                        try:
                            clean_val = str(row['prompt']).strip()
                            if clean_val.startswith('prompt'): clean_val = clean_val[6:].strip()
                            try: p_data = ast.literal_eval(clean_val)
                            except: p_data = json.loads(clean_val)
                        except:
                            # Fallback if parse fails
                            return pd.Series([row['prompt'], "[]", "[]", "[]", "", 0])

                        # B. Retrieve New Dialogues for this Panel
                        d_range = row['dialogue_range']
                        new_texts = []
                        if d_range != "0-0":
                            s, e = map(int, d_range.split('-'))
                            for i in range(s, e + 1):
                                new_texts.append(str(dialogue_map.get(i, "MISSING")))
                        
                        # Create an iterator to feed text into the prompt structure
                        text_iter = iter(new_texts)
                        
                        # C. Initialize Metadata Containers
                        characters = set()
                        sfx_list = []
                        action_texts = []
                        duration = p_data.get('duration', 0)

                        # D. Walk the JSON Structure
                        cuts = p_data.get('cuts', [])
                        for cut in cuts:
                            # Extract Action
                            act = cut.get('action')
                            if act: action_texts.append(str(act))
                            
                            audio = cut.get('audio', {})
                            if isinstance(audio, dict):
                                # Extract SFX / Narration
                                narr = audio.get('narration')
                                if narr and str(narr).strip():
                                    sfx_list.append(str(narr))
                                
                                # Update Dialogue & Collect Characters
                                dial_obj = audio.get('dialogue', {})
                                if isinstance(dial_obj, dict):
                                    for speaker in dial_obj.keys():
                                        characters.add(speaker)
                                        # --- THE UPDATE LOGIC ---
                                        # Overwrite old text with new text from Step 2
                                        try:
                                            dial_obj[speaker] = next(text_iter)
                                        except StopIteration:
                                            pass 

                        # E. Serialize Outputs
                        updated_prompt_str = str(p_data) # Dict back to String
                        merged_dialogues_json = json.dumps(new_texts, ensure_ascii=False)
                        characters_json = json.dumps(list(characters), ensure_ascii=False)
                        sfx_json = json.dumps(sfx_list, ensure_ascii=False)
                        action_str = " | ".join(action_texts)

                        return pd.Series([
                            updated_prompt_str, 
                            merged_dialogues_json, 
                            characters_json, 
                            sfx_json, 
                            action_str, 
                            duration
                        ])

                    # 4. Apply Logic
                    with st.spinner("Injecting new dialogues and extracting metadata context..."):
                        
                        # Define target columns
                        target_cols = [
                            'prompt', 
                            'merged_dialogues', 
                            'characters_included', 
                            'sfx_keywords', 
                            'action_description', 
                            'panel_duration'
                        ]
                        
                        # Run the function on the dataframe
                        df_main[target_cols] = df_main.apply(process_panel, axis=1)

                        st.success("✅ Merge Complete! Prompt column updated.")
                        
                        # 5. Preview
                        st.write("### Context Preview (for OpenAI)")
                        st.dataframe(df_main[['panel_number', 'characters_included', 'sfx_keywords', 'panel_duration', 'action_description']].head())

                        # 6. Download
                        output_final = BytesIO()
                        with pd.ExcelWriter(output_final, engine='openpyxl') as writer:
                            df_main.to_excel(writer, index=False)
                        
                        # Dynamic Filename
                        suffix = st.session_state.get('main_filename_suffix', 'Merged')
                        fname = f"MotionX_Final_Task_{suffix}.xlsx"
                        
                        st.download_button(
                            label="📥 Download Final Task File", 
                            data=output_final.getvalue(), 
                            file_name=fname,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

            else:
                 st.error(f"❌ MISMATCH: Main Sheet expects {count_req} dialogues, but Step 2 provided {count_found}.")
                 st.warning("Please check Step 2: Did you filter the correct Episode? Did you remove too many SFX rows?")

        except Exception as e:
            st.error(f"Error: {e}")