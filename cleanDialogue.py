import streamlit as st
import pandas as pd
from io import BytesIO

def is_sfx(text):
    if pd.isna(text) or str(text).strip() == "": return False
    return str(text).strip().isupper()

def render_dialogue_cleaner():
    st.header("2️⃣ Dialogue Sheet Cleaner")
    st.markdown("Removes SFX rows and assigns `global_dialogue_id`.")

    dialog_file = st.file_uploader("Upload Dialogues Excel (Raw)", type=['xlsx'], key="dialog_uploader")

    if dialog_file:
        try:
            xls_dialog = pd.ExcelFile(dialog_file)
            selected_dialog_sheet = st.selectbox("Select Dialogue Sheet (Source)", xls_dialog.sheet_names)
            df_dialog = pd.read_excel(dialog_file, sheet_name=selected_dialog_sheet)
            
            if 'episode_number' in df_dialog.columns:
                available_eps = sorted(df_dialog['episode_number'].dropna().unique())
                
                default_idx = 0
                if 'selected_episode_num' in st.session_state and st.session_state.selected_episode_num in available_eps:
                    default_idx = available_eps.index(st.session_state.selected_episode_num)
                
                selected_ep_dialog = st.selectbox("Select Episode", available_eps, index=default_idx)
                
                if st.button("Clean & Process Dialogue Sheet"):
                    df_ep = df_dialog[df_dialog['episode_number'] == selected_ep_dialog].copy()
                    
                    clean_rows = []
                    global_id_counter = 1
                    
                    for idx, row in df_ep.iterrows():
                        text = row.get('QC Dialogues') if pd.notna(row.get('QC Dialogues')) else row.get('adapted_dialogue')
                        
                        if is_sfx(text): continue 
                        
                        clean_rows.append({
                            **row.to_dict(),
                            'final_dialogue_text': text,
                            'global_dialogue_id': global_id_counter
                        })
                        global_id_counter += 1
                    
                    df_dialog_clean = pd.DataFrame(clean_rows)

                    # SAVE TO SESSION STATE
                    st.session_state['clean_dialog_df'] = df_dialog_clean
                    st.success("✅ Dialogue Sheet processed and stored in memory! You can now proceed to Step 3.")
                    
                    output_dialog = BytesIO()
                    with pd.ExcelWriter(output_dialog, engine='openpyxl') as writer:
                        df_dialog_clean.to_excel(writer, index=False)
                    
                    st.download_button("📥 Download Cleaned Dialogue Sheet", data=output_dialog.getvalue(),
                                       file_name=f"Cleaned_Dialogues_Ep{selected_ep_dialog}.xlsx")
            else:
                st.error("Column 'episode_number' not found.")
        except Exception as e:
            st.error(f"Error: {e}")