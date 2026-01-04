# 🎬 MotionX Automation Dashboard

An internal Python/Streamlit tool to automate comic script preparation for ElevenLabs. It synchronizes Excel data, updates JSON prompts, and extracts metadata for AI context.

---

## ⚡ Quick Start

**1. Setup (First Run Only)**
```bash
chmod +x setup.sh && ./setup.sh
```

**2. Launch App**
```bash
./run.sh

```

---

## 🔄 Workflow (3-Step Wizard)

**Step 1: Clean Main Sheet**

* Upload your **Main Excel**. Select Episode & Panel Range.
* **Action:** Calculates global dialogue IDs and filters panels.

**Step 2: Clean Dialogue Sheet**

* Upload your **Dialogue Excel**. Select the source sheet (QC).
* **Action:** Removes SFX rows (All-Caps) and assigns matching IDs.

**Step 3: Merge & Validate**

* Auto-loads data from previous steps.
* **Action:** Validates ID counts, updates the `prompt` JSON with new text, and extracts metadata (`action`, `sfx`, `characters`).
* *Download the Final Task File.*

---

## ⚠️ Critical Logic

* **SFX Detection:** Any cell with **ALL UPPERCASE** text (e.g., "STOMP") is treated as SFX and **removed**.
* **Prompt Update:** The tool surgically overwrites the old dialogue inside the Main Sheet's JSON with the clean text from the Dialogue Sheet.

```

```