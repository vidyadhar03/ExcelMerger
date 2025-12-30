# 📖 MotionX Excel Dialogue Merger

A specialized internal tool built with **Python** and **Streamlit** to automate the merging of comic dialogues and SFX into a single production sheet.

This tool intelligently categorizes text based on capitalization:

* **All-Caps (e.g., "BAM BAM")**  Automatically mapped to the `sfx` key.
* **Mixed-Case (e.g., "Wait WHAT")**  Automatically mapped to the `dialogues` key.

---

## 🚀 Quick Start Guide

Follow these steps to get the tool running on your local machine.

### 1. Clone the Repository

Open your terminal and clone this project:

```bash
git clone <your-repository-url>
cd MotionX-Excel-Merger

```

### 2. Initial Setup (First time only)

Run this command to grant permissions and install all necessary components (Python virtual environment and libraries):

```bash
chmod +x *.sh && ./setup.sh

```

### 3. Launch the Tool

Run this command whenever you want to use the merger. It will automatically open the interface in your default web browser:

```bash
./run.sh

```

---

## 🛠 How to Use the Merger

1. **Upload Files:** Drag and drop your **Main Excel Sheet** and your **Dialogue Excel Sheet**.
2. **Select Episode:** Choose the episode number you are working on from the dropdown.
3. **Define Range:** Use the input boxes to set the **Start Panel** and **End Panel** range.
4. **Process:** Click the "Merge and Generate" button.
5. **Download:** Once the preview looks correct, click **📥 Download Merged Excel**.

---

## 📂 Project Structure

* `app.py`: The core logic and Streamlit UI.
* `setup.sh`: Automates the creation of the `venv` and library installation.
* `run.sh`: Activates the environment and launches the app.
* `requirements.txt`: List of Python dependencies (Pandas, Streamlit, Openpyxl).
* `.gitignore`: Configured to prevent local `venv` and private `.xlsx` files from being uploaded.

---

## ⚠️ Important Notes

* **Text Formatting:** The tool relies on **ALL CAPS** to identify Sound Effects (SFX). If a shouting line like "WHAT" should be dialogue, ensure it is written as "What" or "What!".
* **Excel Columns:** Ensure your Dialogue sheet contains the columns: `episode_number`, `image_number`, `dialogue_number`, and `QC Dialogues`.
