import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def initialize_groq(api_key):
    client = Groq(api_key=api_key)
    return client


def ask_groq(client, context, question, compound_data=None, gene_id=None, pdb_ids=None):

    # Build extra structured info
    extra = ""

    if compound_data:
        extra += f"\nCompound: {compound_data['compound']}, Formula: {compound_data['formula']}, Weight: {compound_data['weight']} g/mol"

    if gene_id:
        extra += f"\nAssociated Gene ID (NCBI): {gene_id}"

    if pdb_ids:
        extra += f"\nRelated PDB Structures: {', '.join(pdb_ids)}"

    prompt = f"""
You are a biomedical research assistant specializing in drug discovery.

Context from recent scientific literature:
{context}

Additional structured data:
{extra}

Question:
{question}

Instructions:
- Write a clear, fluent scientific paragraph answering the question.
- Use the context and structured data above to support your answer.
- Mention the compound formula, molecular weight, gene, and protein structures naturally in the paragraph.
- Do NOT use bullet points. Write in flowing paragraph form only.
- Keep it between 5 to 8 sentences.
- Sound like a scientific expert explaining to a researcher.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a biomedical research assistant specializing in drug discovery."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1024,
            temperature=0.7
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Groq API Error: {str(e)}"