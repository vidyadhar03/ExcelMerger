import streamlit as st
import pandas as pd
import json
from io import BytesIO

def render_merger():
    st.header("3️⃣ The Final Merge")
    st.markdown("Validates and generates the final Task Sheet.")

    # --- INPUT HANDLER: Check Memory First, Fallback to Upload ---
    df_main = None
    df_dial = None

    # 1. Check Main Sheet
    if 'clean_main_df' in st.session_state:
        st.info("✅ Main Sheet loaded from Step 1.")
        df_main = st.session_state['clean_main_df']
    else:
        clean_main_file = st.file_uploader("Upload Cleaned Main Sheet", type=['xlsx'], key="merge_main")
        if clean_main_file:
            df_main = pd.read_excel(clean_main_file)

    # 2. Check Dialogue Sheet
    if 'clean_dialog_df' in st.session_state:
        st.info("✅ Dialogue Sheet loaded from Step 2.")
        df_dial = st.session_state['clean_dialog_df']
    else:
        clean_dialog_file = st.file_uploader("Upload Cleaned Dialogue Sheet", type=['xlsx'], key="merge_dialog")
        if clean_dialog_file:
            df_dial = pd.read_excel(clean_dialog_file)

    # --- MERGING LOGIC ---
    if df_main is not None and df_dial is not None:
        st.divider()
        st.subheader("Validation")

        try:
            # A. Get Range Info from Main
            # We filter out rows that have "0-0" (no dialogues) to find the actual start/end IDs
            valid_ranges = df_main[df_main['dialogue_range'] != "0-0"]
            
            if valid_ranges.empty:
                st.warning("⚠️ No dialogues found in the Main Sheet range (All are 0-0). Merge is not needed, but you can still download.")
                count_main_req = 0
                count_dial_found = 0
                start_id_main = 0
                last_id_main = 0
            else:
                start_id_main = int(valid_ranges.iloc[0]['dialogue_range'].split('-')[0])
                last_id_main = int(valid_ranges.iloc[-1]['dialogue_range'].split('-')[1])
                count_main_req = last_id_main - start_id_main + 1
            
                # B. Filter Dialogues to match request
                df_dial_filtered = df_dial[
                    (df_dial['global_dialogue_id'] >= start_id_main) & 
                    (df_dial['global_dialogue_id'] <= last_id_main)
                ]
                count_dial_found = len(df_dial_filtered)

            # C. Display Stats
            c1, c2 = st.columns(2)
            c1.metric("Main Sheet Requests IDs", f"{start_id_main} - {last_id_main}")
            c2.metric("Matching Dialogues Found", count_dial_found, delta=count_dial_found - count_main_req)

            # D. Validation Check
            if count_dial_found == count_main_req:
                if count_main_req > 0:
                    st.success("✅ VALIDATION SUCCESSFUL")
                
                if st.button("🚀 Merge & Generate Final Task File", type="primary"):
                    
                    # 1. Create Lookup Map (ID -> Text)
                    if not valid_ranges.empty:
                        dialogue_map = pd.Series(
                            df_dial_filtered.final_dialogue_text.values,
                            index=df_dial_filtered.global_dialogue_id
                        ).to_dict()
                    else:
                        dialogue_map = {}
                    
                    # 2. Inject Dialogues Logic
                    def inject_dialogues(row):
                        if row['dialogue_range'] == "0-0":
                            return "[]"
                        try:
                            s, e = map(int, row['dialogue_range'].split('-'))
                            # Create list of dialogues for this panel
                            d_list = []
                            for i in range(s, e + 1):
                                txt = dialogue_map.get(i, "ERROR: MISSING")
                                d_list.append(str(txt))
                            
                            return json.dumps(d_list, ensure_ascii=False)
                        except:
                            return "[]"

                    # 3. Apply to DataFrame
                    df_main['merged_dialogues'] = df_main.apply(inject_dialogues, axis=1)
                    
                    # 4. Preview
                    st.write("### Final Result Preview")
                    st.dataframe(df_main[['panel_number', 'dialogue_range', 'merged_dialogues']].head())
                    
                    # 5. Download
                    output_final = BytesIO()
                    with pd.ExcelWriter(output_final, engine='openpyxl') as writer:
                        df_main.to_excel(writer, index=False)
                    
                    # Generate Filename using suffix from Step 1
                    suffix = st.session_state.get('main_filename_suffix', 'Merged')
                    fname = f"Final_Task_{suffix}.xlsx"
                    
                    st.download_button(
                        label="📥 Download Final Merged Sheet",
                        data=output_final.getvalue(),
                        file_name=fname,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error(f"❌ MISMATCH: Main sheet needs {count_main_req} dialogues, but found {count_dial_found}.")
                st.warning("Troubleshooting:\n1. Did you remove too many SFX rows in Step 2?\n2. Did you select the correct Episode in Step 2?")

        except Exception as e:
            st.error(f"Error during validation: {e}")