import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def initialize_openai(api_key):
    client = OpenAI(api_key=api_key)
    return client

def ask_openai(client, context, question, compound_data=None, gene_id=None, pdb_ids=None):
    # Build extra structured info
    extra = ""
    if compound_data:
        extra += f"\nCompound: {compound_data['compound']}, Formula: {compound_data['formula']}, Weight: {compound_data['weight']} g/mol"
    if gene_id:
        extra += f"\nAssociated Gene ID (NCBI): {gene_id}"
    if pdb_ids:
        extra += f"\nRelated PDB Structures: {', '.join(pdb_ids)}"

    prompt = f"""
You are a helpful assistant explaining drug discovery to a beginner.

Context from recent scientific literature:
{context}

Additional data:
{extra}

Question:
{question}

Instructions:
- Write a clear, simple paragraph answering the question.
- Explain it so a high schooler or a non-scientist can easily understand. 
- Avoid complex jargon. If you must use a scientific term, briefly explain what it means.
- Mention the compound formula, weight, and gene naturally, but keep the focus on the big picture.
- Keep it between 4 to 6 sentences.
- Do NOT use bullet points. Write in plain text only so you do not break the frontend UI.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful, easy-to-understand science communicator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.4 # Lower temperature keeps it focused and less prone to rambling
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"OpenAI API Error: {str(e)}"