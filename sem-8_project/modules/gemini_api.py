from google import genai


def initialize_gemini(api_key):

    client = genai.Client(api_key=api_key)

    return client


def ask_gemini(client, context, question):

    prompt = f"""
You are a biomedical research assistant.

Context:
{context}

Question:
{question}

Give a clear scientific explanation.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return response.text