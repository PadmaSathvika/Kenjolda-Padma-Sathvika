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
    "search_chembl": {
        "description": "Search ChEMBL for drug targets, clinical phases, and bioactivity",
        "use_when": ["chembl", "target", "disease", "bioactivity", "ic50", "affinity", "phase"]
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

def decide_tools(question):
    question_lower = question.lower()
    selected_tools = []

    for tool_name, tool_info in TOOLS.items():
        for keyword in tool_info["use_when"]:
            if keyword in question_lower:
                if tool_name not in selected_tools:
                    selected_tools.append(tool_name)
                break

    if not selected_tools:
        selected_tools = ["search_pubmed", "get_pubchem", "search_chembl"]

    if "run_docking" in selected_tools:
        if "search_pdb" not in selected_tools: selected_tools.append("search_pdb")
        if "clean_pdb" not in selected_tools: selected_tools.append("clean_pdb")

    if "search_chembl" not in selected_tools:
        selected_tools.append("search_chembl")

    return selected_tools

def generate_plan(question, selected_tools, client):
    tools_list = "\n".join([f"- {t}: {TOOLS[t]['description']}" for t in selected_tools])

    prompt = f"""
You are an AI assistant planning a drug discovery task.
The user asked: "{question}"
You have decided to use the following tools:
{tools_list}

Generate a clear, simple step-by-step plan explaining:
1. Why each tool is needed.
2. What simple information you expect to get.

Keep it very short - maximum 5 steps. Write in plain text, no bullet points. Do NOT use complex scientific jargon.
"""
    try:
        response = client.chat.completions.create(
            model="gemini-3-flash-preview", 
            messages=[
                {"role": "system", "content": "You are a helpful, easy-to-understand planning assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Could not generate plan: {str(e)}"

def synthesize_answer(question, collected_data, client):
    context = ""

    if "pubmed_abstracts" in collected_data:
        context += "\nScientific Literature:\n"
        for r in collected_data["pubmed_abstracts"][:3]:
            context += f"- [{r['metadata']['year']}] {r['metadata']['title']}\n  {r['text'][:300]}...\n"

    if "chembl_data" in collected_data and collected_data["chembl_data"]:
        context += f"\nChEMBL Database Matches:\n"
        for c in collected_data["chembl_data"]:
            context += f"- ID: {c['chembl_id']}, Name: {c['name']}, Max Clinical Phase: {c['max_phase']}\n"

    if "compound_data" in collected_data and collected_data["compound_data"]:
        c = collected_data["compound_data"]
        context += f"\nCompound Data:\n- Name: {c['compound']}\n- Formula: {c['formula']}\n- Weight: {c['weight']} g/mol\n"

    if "gene_id" in collected_data and collected_data["gene_id"]:
        context += f"\nGene Data:\n- NCBI Gene ID: {collected_data['gene_id']}\n"

    if "pdb_info" in collected_data and collected_data["pdb_info"]:
        context += f"\nProtein Structure Details:\n"
        for info in collected_data["pdb_info"]:
            if info: context += f"- Protein: {info['protein_name']} | Chains: {info['num_chains']} | Atoms: {info['num_atoms']}\n"

    if "docking_results" in collected_data and collected_data["docking_results"]:
        context += f"\nMolecular Docking Results:\n"
        for dr in collected_data["docking_results"]:
            context += f"- {dr}\n"

    prompt = f"""
Here is the data collected from multiple databases:
{context}

Question: {question}

Instructions:
- You are a helpful, super conversational, and highly technical AI assistant. Talk exactly like a real person helping a friend with a project.
- Do NOT act like a formal teacher. No cheesy greetings like "Hello there, wonderful student!"
- Use a casual, friendly, and energetic tone (e.g., "Alright, let's break this down," "Here is the deal," "Check this out").
- Get straight to the point. You have the data from the databases, now explain it simply.
- Format the response beautifully using Markdown. Use bold text for key terms and bullet points for the data.
- Mention the compound formula, weight, clinical phases, and gene ID naturally.
- Keep it snappy, complete your sentences, and do not cut off!
"""
    try:
        response = client.chat.completions.create(
            model="gemini-3-flash-preview", 
            messages=[
                {"role": "system", "content": "You are a casual, highly technical AI assistant helping a friend. Talk like a normal human software engineer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,  # Bumped this up so it doesn't get cut off!
            temperature=0.7 
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Could not synthesize answer: {str(e)}"