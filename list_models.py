#!/usr/bin/env python3
"""
Helper script to list available Gemini models.
Requires GOOGLE_API_KEY environment variable to be set.
"""

import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ Error: GOOGLE_API_KEY environment variable not set.")
    print("Set it with: export GOOGLE_API_KEY='your_key_here'")
    exit(1)

client = genai.Client(api_key=api_key)

print("📋 Available Gemini Models:\n")
try:
    models = client.models.list()
    for model in models:
        print(f"  ✓ {model.name}")
        if hasattr(model, 'display_name') and model.display_name:
            print(f"    Display Name: {model.display_name}")
        print()
except Exception as e:
    print(f"❌ Error listing models: {e}")
    print("\n💡 Tip: Make sure GOOGLE_API_KEY is set correctly.")

