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

    # Check Main Sheet
    if 'clean_main_df' in st.session_state:
        st.info("✅ Main Sheet loaded from Step 1.")
        df_main = st.session_state['clean_main_df']
    else:
        clean_main_file = st.file_uploader("Upload Cleaned Main Sheet", type=['xlsx'], key="merge_main")
        if clean_main_file: df_main = pd.read_excel(clean_main_file)

    # Check Dialogue Sheet
    if 'clean_dialog_df' in st.session_state:
        st.info("✅ Dialogue Sheet loaded from Step 2.")
        df_dial = st.session_state['clean_dialog_df']
    else:
        clean_dialog_file = st.file_uploader("Upload Cleaned Dialogue Sheet", type=['xlsx'], key="merge_dialog")
        if clean_dialog_file: df_dial = pd.read_excel(clean_dialog_file)

    # --- MERGING LOGIC ---
    if df_main is not None and df_dial is not None:
        st.divider()
        st.subheader("Validation")

        try:
            # 1. Get Range Info from Main
            valid_ranges = df_main[df_main['dialogue_range'] != "0-0"]
            if valid_ranges.empty:
                st.warning("No dialogues found in the Main Sheet range.")
                return

            first_range = valid_ranges.iloc[0]['dialogue_range']
            last_range = valid_ranges.iloc[-1]['dialogue_range']
            
            start_id_main = int(first_range.split('-')[0])
            last_id_main = int(last_range.split('-')[1])
                
            # 2. Filter Dialogues
            df_dial_filtered = df_dial[
                (df_dial['global_dialogue_id'] >= start_id_main) & 
                (df_dial['global_dialogue_id'] <= last_id_main)
            ]
            
            count_main_req = last_id_main - start_id_main + 1
            count_dial_found = len(df_dial_filtered)
            
            c1, c2 = st.columns(2)
            c1.metric("Main Sheet Requests IDs", f"{start_id_main} - {last_id_main}")
            c2.metric("Matching Dialogues Found", count_dial_found, delta=count_dial_found - count_main_req)

            if count_dial_found == count_main_req:
                st.success("✅ VALIDATION SUCCESSFUL")
                
                if st.button("🚀 Merge & Generate Final Task File"):
                    dialogue_map = pd.Series(
                        df_dial_filtered.final_dialogue_text.values,
                        index=df_dial_filtered.global_dialogue_id
                    ).to_dict()
                    
                    def inject_dialogues(row):
                        if row['dialogue_range'] == "0-0": return "[]"
                        try:
                            s, e = map(int, row['dialogue_range'].split('-'))
                            return json.dumps([str(dialogue_map.get(i, "ERROR")) for i in range(s, e + 1)], ensure_ascii=False)
                        except: return "[]"

                    df_main['merged_dialogues'] = df_main.apply(inject_dialogues, axis=1)
                    
                    st.write("### Final Result Preview")
                    st.dataframe(df_main[['panel_number', 'dialogue_range', 'merged_dialogues']].head())
                    
                    output_final = BytesIO()
                    with pd.ExcelWriter(output_final, engine='openpyxl') as writer:
                        df_main.to_excel(writer, index=False)
                    
                    st.download_button("📥 Download Final Merged Sheet", data=output_final.getvalue(),
                                       file_name="MotionX_Final_Merged_Task.xlsx")
            else:
                st.error(f"❌ MISMATCH: Main sheet needs {count_main_req} dialogues, but found {count_dial_found}.")
                st.warning("Check if SFX removal in Step 2 was too aggressive, or if the Main Sheet range is correct.")

        except Exception as e:
            st.error(f"Error during validation: {e}")