import streamlit as st
import pandas as pd
import json
import re

st.set_page_config(page_title="Dialogue & SFX Merger", layout="wide")

def classify_text(text):
    if pd.isna(text) or str(text).strip() == "":
        return None
    # Tokenize: find all words
    tokens = re.findall(r'\b\w+\b', str(text))
    if not tokens:
        return "dialogues"
    # If all tokens are uppercase, it's SFX (e.g., "BAM BAM")
    if all(t.isupper() for t in tokens):
        return "sfx"
    return "dialogues"

st.title("📖 Dialogue Object Merger")
st.markdown("Upload your Main Sheet and Dialogue Sheet to merge them into JSON objects.")

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

    # --- DATA ANALYSIS ---
    episodes = df_dialog['episode_number'].unique()
    selected_ep = st.selectbox("Select Episode", sorted(episodes))
    
    # Filter dialog for summary
    ep_dialog = df_dialog[df_dialog['episode_number'] == selected_ep]
    min_panel = int(ep_dialog['image_number'].min())
    max_panel = int(ep_dialog['image_number'].max())

    st.info(f"Detected Panels for Episode {selected_ep}: **{min_panel} to {max_panel}**")

    # --- RANGE SELECTION ---
    range_col1, range_col2 = st.columns(2)
    with range_col1:
        start_p = st.number_input("Start Panel", value=min_panel, min_value=min_panel, max_value=max_panel)
    with range_col2:
        end_p = st.number_input("End Panel", value=max_panel, min_value=min_panel, max_value=max_panel)

    if st.button("Merge and Generate New Sheet"):
        # Process only the selected range
        mask = (df_dialog['episode_number'] == selected_ep) & \
               (df_dialog['image_number'] >= start_p) & \
               (df_dialog['image_number'] <= end_p)
        df_filtered = df_dialog[mask].copy()

        # Group dialogues into the required JSON structure
        json_map = {}
        for (img_num), group in df_filtered.groupby('image_number'):
            panel_obj = {"dialogues": {}, "sfx": {}}
            for _, row in group.iterrows():
                d_id = str(row['dialogue_number'])
                # Priority: QC Dialogues -> adapted_dialogue
                txt = row['QC Dialogues'] if pd.notna(row['QC Dialogues']) else row['adapted_dialogue']
                
                category = classify_text(txt)
                if category:
                    panel_obj[category][d_id] = str(txt).strip()
            
            json_map[img_num] = json.dumps(panel_obj, ensure_ascii=False)

        # Map back to main sheet
        def apply_json(row):
            if row['episode_number'] == selected_ep and row['panel_number'] in json_map:
                return json_map[row['panel_number']]
            return None

        df_main['dialogue_json'] = df_main.apply(apply_json, axis=1)

        # Download Button
        st.write("### Preview of Processed Data")
        st.dataframe(df_main[df_main['dialogue_json'].notna()].head())

        # Save to Excel in Memory
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_main.to_excel(writer, index=False)
        processed_data = output.getvalue()

        st.download_button(
            label="📥 Download Merged Excel",
            data=processed_data,
            file_name=f"Merged_Ep{selected_ep}_Panels_{start_p}-{end_p}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )