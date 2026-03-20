import os
from dotenv import load_dotenv
from modules.gemini_api import initialize_gemini, ask_gemini

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env file")
    exit(1)

model = initialize_gemini(API_KEY)

context = """
Heme is an iron-containing compound that forms the prosthetic group of hemoglobin.
It allows hemoglobin to bind oxygen in red blood cells.
"""

question = "What is the function of heme in hemoglobin?"

answer = ask_gemini(model, context, question)

print("\nGemini Answer:\n")
print(answer)