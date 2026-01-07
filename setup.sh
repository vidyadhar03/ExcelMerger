#!/bin/bash
echo "🚀 Starting setup..."

# 1. Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created."
fi

# 2. Activate and install dependencies
source venv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
python3 -m streamlit run app.py

echo "✅ All dependencies installed."
echo "----------------------------------------"
echo "To start the tool, run: source venv/bin/activate && streamlit run app.py"
echo "----------------------------------------"