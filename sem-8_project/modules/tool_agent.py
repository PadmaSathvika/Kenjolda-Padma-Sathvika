import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


# ============================
# Tool Definitions
# ============================

TOOLS = {
    "search_pubmed": {
        "description": "Search PubMed for scientific papers on a given topic",
        "use_when": ["papers", "research", "literature", "studies", "publications", "articles"]
    },
    "search_pdb": {
        "description": "Search Protein Data Bank for 3D protein structures",
        "use_when": ["protein", "structure", "pdb", "binding", "receptor", "enzyme", "3d"]
    },
    "get_pubchem": {
        "description": "Get chemical compound information from PubChem",
        "use_when": ["compound", "drug", "chemical", "formula", "molecule", "weight", "smiles"]
    },
    "get_gene": {
        "description": "Get gene information from NCBI",
        "use_when": ["gene", "genome", "expression", "mutation", "dna", "rna", "ncbi"]
    },
    "clean_pdb": {
        "description": "Clean and prepare PDB files for docking",
        "use_when": ["clean", "prepare", "docking", "simulation", "dock"]
    },
    "run_docking": {
        "description": "Run automated molecular docking simulation",
        "use_when": ["docking", "binding", "affinity", "simulate", "vina", "dock"]
    }
}


# ============================
# Decide which tools to use
# ============================

def decide_tools(question):
    """
    Multi-step reasoning to decide which tools to call
    based on the user's question.
    """

    question_lower = question.lower()
    selected_tools = []

    for tool_name, tool_info in TOOLS.items():
        for keyword in tool_info["use_when"]:
            if keyword in question_lower:
                if tool_name not in selected_tools:
                    selected_tools.append(tool_name)
                break

    # Always include pubmed and pubchem for drug discovery questions
    if not selected_tools:
        selected_tools = ["search_pubmed", "get_pubchem"]

    # If docking is requested, also need pdb and clean
    if "run_docking" in selected_tools:
        if "search_pdb" not in selected_tools:
            selected_tools.append("search_pdb")
        if "clean_pdb" not in selected_tools:
            selected_tools.append("clean_pdb")

    return selected_tools


# ============================
# Generate reasoning plan
# ============================

def generate_plan(question, selected_tools, client):
    """
    Use Groq to generate a multi-step reasoning plan
    before executing the tools.
    """

    tools_list = "\n".join([
        f"- {t}: {TOOLS[t]['description']}"
        for t in selected_tools
    ])

    prompt = f"""
You are an expert biomedical research agent specializing in drug discovery.

The user asked: "{question}"

You have decided to use the following tools:
{tools_list}

Generate a clear step-by-step reasoning plan explaining:
1. Why each tool is needed
2. What information you expect to get from each tool
3. How you will combine the results to answer the question

Keep it concise - maximum 5 steps. Write in plain text, no bullet points.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert biomedical research agent."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=512,
            temperature=0.3
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Could not generate plan: {str(e)}"


# ============================
# Synthesize final answer
# ============================

def synthesize_answer(question, collected_data, client):
    """
    Use Groq to synthesize all collected data into
    a final scientific paragraph answer.
    """

    # Build context from all collected data
    context = ""

    if "pubmed_abstracts" in collected_data:
        context += "\nScientific Literature:\n"
        for r in collected_data["pubmed_abstracts"][:3]:
            context += f"- [{r['metadata']['year']}] {r['metadata']['title']}\n"
            context += f"  {r['text'][:300]}...\n"

    if "compound_data" in collected_data and collected_data["compound_data"]:
        c = collected_data["compound_data"]
        context += f"\nCompound Data:\n"
        context += f"- Name: {c['compound']}\n"
        context += f"- Formula: {c['formula']}\n"
        context += f"- Molecular Weight: {c['weight']} g/mol\n"

    if "gene_id" in collected_data and collected_data["gene_id"]:
        context += f"\nGene Data:\n"
        context += f"- NCBI Gene ID: {collected_data['gene_id']}\n"

    if "pdb_ids" in collected_data and collected_data["pdb_ids"]:
        context += f"\nProtein Structures:\n"
        for pdb in collected_data["pdb_ids"]:
            context += f"- PDB ID: {pdb}\n"

    if "pdb_info" in collected_data and collected_data["pdb_info"]:
        context += f"\nProtein Structure Details:\n"
        for info in collected_data["pdb_info"]:
            if info:
                context += f"- Protein: {info['protein_name']}\n"
                context += f"  Chains: {info['num_chains']}, "
                context += f"Residues: {info['num_residues']}, "
                context += f"Atoms: {info['num_atoms']}\n"

    if "docking_results" in collected_data and collected_data["docking_results"]:
        context += f"\nMolecular Docking Results:\n"
        for dr in collected_data["docking_results"]:
            context += f"- {dr}\n"

    prompt = f"""
You are a biomedical research assistant specializing in drug discovery.

Here is all the data collected from multiple scientific databases:
{context}

Question: {question}

Instructions:
- Write a comprehensive, fluent scientific paragraph answering the question.
- Naturally incorporate the compound formula, molecular weight, gene ID, and protein structures.
- If docking results are available, mention binding affinities.
- Do NOT use bullet points. Write in flowing paragraph form only.
- Keep it between 6 to 10 sentences.
- Sound like a scientific expert writing a research summary.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert biomedical research assistant."
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
        return f"Could not synthesize answer: {str(e)}"