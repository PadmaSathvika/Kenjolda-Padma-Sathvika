from modules.gemini_api import initialize_gemini, ask_gemini

API_KEY = "AIzaSyCxYoPZAF5YFjiJblWU3ne-s4anKAmx8j4"

client = initialize_gemini(API_KEY)

context = """
Heme is an iron-containing compound that forms the prosthetic group of hemoglobin.
It allows hemoglobin to bind oxygen in red blood cells.
"""

question = "What is the function of heme in hemoglobin?"

answer = ask_gemini(client, context, question)

print("\nGemini Answer:\n")
print(answer)