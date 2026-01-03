import streamlit as st
import pandas as pd
from io import BytesIO

def is_sfx(text):
    """
    Returns True if text is likely SFX (All Uppercase).
    Handles: "STOMP", "PAT PAT", "WARNING! WARNING!"
    """
    if pd.isna(text) or str(text).strip() == "":
        return False
    
    clean_text = str(text).strip()
    # Check if it has at least one letter and ALL letters are uppercase
    return clean_text.isupper()

def render_dialogue_cleaner():
    st.header("2️⃣ Dialogue Sheet Cleaner")
    st.markdown("Removes SFX rows and assigns `global_dialogue_id` to match the Main Sheet.")

    dialog_file = st.file_uploader("Upload Dialogues Excel (Raw)", type=['xlsx'], key="dialog_uploader")

    if dialog_file:
        try:
            xls_dialog = pd.ExcelFile(dialog_file)
            dialog_sheets = xls_dialog.sheet_names
            
            # 1. Sheet Selector
            selected_dialog_sheet = st.selectbox("Select Dialogue Sheet (Source)", dialog_sheets)
            
            # Load Data
            df_dialog = pd.read_excel(dialog_file, sheet_name=selected_dialog_sheet)
            
            # 2. Episode Selector (Detect from Column)
            if 'episode_number' in df_dialog.columns:
                available_eps = sorted(df_dialog['episode_number'].dropna().unique())
                
                # Auto-select episode if detected in Step 1
                default_idx = 0
                if 'selected_episode_num' in st.session_state and st.session_state.selected_episode_num in available_eps:
                    default_idx = available_eps.index(st.session_state.selected_episode_num)
                
                selected_ep_dialog = st.selectbox("Select Episode to Clean", available_eps, index=default_idx)
                
                if st.button("Clean & Process Dialogue Sheet", type="primary"):
                    with st.spinner("Processing Dialogues..."):
                        # Filter by Episode
                        df_ep = df_dialog[df_dialog['episode_number'] == selected_ep_dialog].copy()
                        
                        # 3. SFX Removal & ID Assignment
                        clean_rows = []
                        global_id_counter = 1
                        
                        for idx, row in df_ep.iterrows():
                            # Prioritize QC Dialogues, fallback to adapted_dialogue
                            text = row.get('QC Dialogues')
                            if pd.isna(text):
                                text = row.get('adapted_dialogue')
                            
                            # Check SFX
                            if is_sfx(text):
                                continue # Skip SFX rows entirely
                            
                            # It is a valid dialogue
                            row_data = row.to_dict()
                            row_data['final_dialogue_text'] = text
                            row_data['global_dialogue_id'] = global_id_counter
                            clean_rows.append(row_data)
                            global_id_counter += 1
                        
                        df_dialog_clean = pd.DataFrame(clean_rows)
                        
                        # Save to Session State (for Merger Tab)
                        st.session_state['clean_dialog_df'] = df_dialog_clean

                        st.success(f"✅ Processed! Found {len(df_dialog_clean)} valid dialogue lines.")
                        
                        # --- ACTION AREA ---
                        st.divider()
                        col_d, col_next = st.columns([1, 1])
                        
                        # Download Button
                        output_dialog = BytesIO()
                        with pd.ExcelWriter(output_dialog, engine='openpyxl') as writer:
                            df_dialog_clean.to_excel(writer, index=False)
                        
                        clean_filename = f"Cleaned_Dialogues_Ep{selected_ep_dialog}.xlsx"
                        
                        col_d.download_button(
                            label="📥 Download Cleaned Sheet",
                            data=output_dialog.getvalue(),
                            file_name=clean_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        # Navigation Button
                        if col_next.button("👉 Go to Step 3 (Merge)"):
                            st.session_state['current_step'] = "3. Merge & Validate"
                            st.rerun()

            else:
                st.error("❌ Column 'episode_number' not found in this sheet.")

        except Exception as e:
            st.error(f"Error reading Dialogue file: {e}")