TOOLS = {
    "get_pubmed": {
        "description": "Search PubMed for scientific papers on a given topic",
        "use_when": ["papers", "research", "literature", "studies", "publications", "articles", "recent"]
    },
    "search_pdb": {
        "description": "Search Protein Data Bank for 3D protein structures",
        "use_when": ["protein", "structure", "pdb", "binding", "binds", "bind", "receptor", "enzyme", "3d", "visualize"]
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
        "use_when": ["docking", "binding", "binds", "bind", "affinity", "simulate", "vina", "dock", "interact", "visualize"]
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
                
    # Baseline for general research
    if not selected_tools:
        selected_tools = ["get_pubmed", "get_pubchem", "search_chembl"]
        
    # Crucial Docking Dependency: Must fetch and clean target before docking
    if "run_docking" in selected_tools:
        if "search_pdb" not in selected_tools: 
            selected_tools.append("search_pdb")
        if "clean_pdb" not in selected_tools: 
            selected_tools.append("clean_pdb")
            
    if "search_chembl" not in selected_tools:
        selected_tools.append("search_chembl")
        
    return selected_tools


def generate_plan(question, selected_tools, client):
    tools_list = "\n".join([f"- {t}: {TOOLS[t]['description']}" for t in selected_tools])
    prompt = f"""You are an AI planning a drug discovery task. User asked: "{question}"\nTools:\n{tools_list}\nGenerate a simple 5-step plan."""
    try:
        response = client.chat.completions.create(
            model="gemini-3-flash-preview", 
            messages=[{"role": "system", "content": "You are a helpful planner."}, {"role": "user", "content": prompt}],
            max_tokens=300, temperature=0.3
        )
        return response.choices[0].message.content
    except Exception:
        return "Could not generate plan."


def synthesize_answer(question, collected_data, client):
    context = ""
    if "pubmed_abstracts" in collected_data:
        context += "\nScientific Literature:\n"
        for r in collected_data["pubmed_abstracts"][:3]: context += f"- [{r['metadata']['year']}] {r['metadata']['title']}\n"
    if "chembl_data" in collected_data and collected_data["chembl_data"]:
        context += f"\nChEMBL Database Matches:\n"
        for c in collected_data["chembl_data"]: context += f"- ID: {c['chembl_id']}, Phase: {c['max_phase']}\n"
    if "compound_data" in collected_data and collected_data["compound_data"]:
        c = collected_data["compound_data"]
        context += f"\nCompound Data:\n- Name: {c['compound']}\n- Formula: {c['formula']}\n- Weight: {c['weight']} g/mol\n"
    if "gene_id" in collected_data and collected_data["gene_id"]:
        context += f"\nGene Data:\n- NCBI Gene ID: {collected_data['gene_id']}\n"
    if "docking_results" in collected_data and collected_data["docking_results"]:
        context += f"\nMolecular Docking Results:\n"
        for dr in collected_data["docking_results"]: context += f"- {dr}\n"


    system_prompt = """You are Gemini, a highly helpful, energetic AI assistant. 
You are speaking to a university student presenting this AI-driven drug discovery pipeline for their final-year project defense.
1. Validate questions with natural transitions ("Alright, let's break this down").
2. Explain the data enthusiastically.
3. Keep formatting clean using Markdown.
4. Mention compound formula, weight, clinical phases, and gene ID.
5. If 'docking_results' are present, tell the user: "I've triggered UCSF Chimera to open so we can visualize the 3D docking results."
6. Keep it under 4 paragraphs and finish your final sentence!"""


    try:
        response = client.chat.completions.create(
            model="gemini-3-flash-preview", 
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Data:\n{context}\n\nQuestion: {question}"}],
            max_tokens=3000, temperature=0.7 
        )
        return response.choices[0].message.content
    except Exception:
        return "Could not synthesize answer."