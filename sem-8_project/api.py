import os
import sys
import json
import subprocess
import tempfile
import traceback
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.corpus import stopwords
from openai import OpenAI

# ============================
# Secure .env Loading & GEMINI API SETUP
# ============================
current_folder = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_folder, ".env")
load_dotenv(dotenv_path=env_path)

my_gemini_key = os.environ.get("GEMINI_API_KEY")

if my_gemini_key:
    print("✅ SUCCESS: Gemini API Key loaded securely from .env!")
else:
    print("❌ ERROR: Could not find GEMINI_API_KEY in .env!")

openai_client = OpenAI(
    api_key=my_gemini_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
) if my_gemini_key else None

# ============================
# Import all modules
# ============================
from modules.pubmed_api import get_pubmed
from modules.pdb_api import search_pdb
from modules.pubchem_api import get_pubchem
from modules.chembl_api import search_chembl
from modules.ncbi_api import get_gene
from modules.downloader import download_structures
from modules.pdb_cleaner import clean_pdb_files, extract_pdb_info
from modules.tool_agent import decide_tools, generate_plan, synthesize_answer
from modules.report_generator import generate_report
from modules.docking import run_docking_pipeline
from modules.rag_database import fetch_pubmed_abstracts, create_vector_database, search_vector_database

# ============================
# Download NLTK data safely
# ============================
try:
    nltk.download("punkt", quiet=True)
    nltk.download("averaged_perceptron_tagger", quiet=True)
    nltk.download("stopwords", quiet=True)
except Exception:
    pass

app = FastAPI(title="AgentDKI Drug Discovery API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
agent_memory = []
tool_stats = {
    "pubmed": {"calls": 0, "status": "active", "last_used": None},
    "pdb": {"calls": 0, "status": "active", "last_used": None},
    "pubchem": {"calls": 0, "status": "active", "last_used": None},
    "chembl": {"calls": 0, "status": "active", "last_used": None},
    "ncbi": {"calls": 0, "status": "active", "last_used": None},
    "docking": {"calls": 0, "status": "idle", "last_used": None},
    "rag": {"calls": 0, "status": "active", "last_used": None},
    "openai": {"calls": 0, "status": "active", "last_used": None},
}
agent_steps = []
rag_index = None
rag_texts = []
rag_metadata = []


class AgentRequest(BaseModel):
    question: str
    year_filter: Optional[int] = None


# ============================
# FOOLPROOF NLP EXTRACTOR
# ============================
def extract_topic_nlp(question):
    tokens = word_tokenize(question)
    tagged = pos_tag(tokens)
    stop_words = set(stopwords.words("english"))

    generic = {
        "role", "effect", "use", "function", "discovery", "research",
        "study", "tell", "explain", "describe", "simulation", "docking",
        "structure", "protein", "target", "find", "molecular", "interaction",
        "treatment", "investigating", "latest", "findings", "developments",
        "show", "run", "give", "make", "test", "analysis", "results",
        "evaluate", "binding", "affinity", "efficacy", "clinical"
    }

    proper_nouns = [word for word, tag in tagged if tag == "NNP" and word.lower() not in stop_words and word.lower() not in generic]
    if proper_nouns:
        return proper_nouns[0]

    common_nouns = [word for word, tag in tagged if tag.startswith("NN") and word.lower() not in stop_words and word.lower() not in generic]
    if common_nouns:
        return common_nouns[0]

    for word, tag in tagged:
        if word.lower() not in stop_words and word.isalpha():
            return word
    return question.split()[0]


def add_step(step_type, tool, content):
    step = {"type": step_type, "tool": tool, "content": content, "timestamp": datetime.now().strftime("%H:%M:%S")}
    agent_steps.append(step)


def update_tool(tool_name, status="active"):
    if tool_name in tool_stats:
        tool_stats[tool_name]["calls"] += 1
        tool_stats[tool_name]["status"] = status
        tool_stats[tool_name]["last_used"] = datetime.now().strftime("%H:%M:%S")


# ============================
# CHIMERA LAUNCHER (DOCKED COMPLEX) - UPDATED VIZ
# ============================
def open_chimera_docked_complex(receptor_path: str, ligand_path: str, topic: str = "Drug Analysis"):
    """
    Launches UCSF Chimera with a protein-ligand complex and highlights
    the docked ligand with bright magenta carbons so it pops out of the ribbon.
    """
    chimera_paths = [
        r"C:\Program Files\Chimera 1.17.3\bin\chimera.exe",
        r"C:\Program Files\UCSF Chimera 1.17\bin\chimera.exe",
        r"C:\Program Files\UCSF Chimera 1.16\bin\chimera.exe",
        r"C:\Program Files\Chimera 1.18\bin\chimera.exe",
        "chimera"
    ]

    if not receptor_path or not os.path.exists(receptor_path):
        print("[Chimera] Error: Receptor file not found")
        return False

    has_ligand = ligand_path and ligand_path != "None" and os.path.exists(ligand_path)

    if receptor_path.endswith('.pdbqt'):
        receptor_pdb = receptor_path.replace(".pdbqt", "_for_viz.pdb")
        try:
            with open(receptor_path, 'r') as f:
                lines = [line[:66].rstrip() + "\n" for line in f
                         if line.startswith("ATOM") or line.startswith("HETATM")]
            with open(receptor_pdb, 'w') as f:
                f.writelines(lines)
                f.write("END\n")
        except Exception as e:
            print(f"[Chimera] Receptor conversion error: {e}")
            receptor_pdb = receptor_path
    else:
        receptor_pdb = receptor_path

    rec_abs = os.path.abspath(receptor_pdb).replace("\\", "/")

    # ---- Build Chimera (Python 2.7) script ----
    viz_script = f"""
import chimera
from chimera import runCommand as rc

# ---- Load receptor ----
try:
    chimera.openModels.open(r'''{rec_abs}''', 'PDB')
except Exception as e:
    rc("2dlabels create err text 'Error loading receptor' color red size 20 xpos .1 ypos .5")

rc("background solid white")
rc("ksdssp")

# ---- Protein: clean tan ribbon ----
rc("~display #0")
rc("ribbon #0")
rc("ribrepr rounded #0")
rc("color tan,r #0")
rc("~ribinsidecolor #0")

# ---- Hide bulk waters ----
rc("~display #0 & solvent")

# ---- Native cofactors / crystal ligands (orange phosphate etc.) ----
rc("display #0 & ligand")
rc("represent stick #0 & ligand")
rc("color byhet #0 & ligand")
"""

    if has_ligand:
        lig_abs = os.path.abspath(ligand_path).replace("\\", "/")
        viz_script += f"""
# ---- Load DOCKED LIGAND as model #1 ----
try:
    chimera.openModels.open(r'''{lig_abs}''', 'PDB')
except Exception as e:
    rc("2dlabels create err text 'Error loading ligand' color red size 20 xpos .1 ypos .6")

# ---- Make docked ligand highly visible ----
rc("display #1")
rc("represent stick #1")
rc("setattr m stickScale 1.8 #1")      # thicker sticks
rc("color magenta #1")                  # magenta carbons (pops against tan)
rc("color byhet #1")                    # N=blue, O=red, S=yellow overlay

# ---- Binding-site residues within 5 A of docked ligand ----
rc("select #1 zr < 5")
rc("~select #1")
rc("display sel")
rc("represent stick sel")
rc("color byhet sel")
# hide ribbon near ligand so it doesn't occlude the view
rc("~ribbon sel")
rc("~select")

# ---- Receptor<->ligand hydrogen bonds ----
rc("hbonds intermodel true intramodel false reveal true color yellow linewidth 2 makePseudobonds true")

# ---- Camera: zoom hard into the binding site ----
rc("focus #1")
rc("cofr #1")
rc("scale 2.2")
"""
    else:
        viz_script += """
rc("focus #0")
"""

    viz_script += f"""
# ---- Titles ----
rc("2dlabels create title text 'Analysis: {topic}' color black size 22 xpos .03 ypos .95")
rc("2dlabels create sub text 'Automated by Agentic AI' color blue size 12 xpos .03 ypos .91")
"""

    temp_dir = tempfile.gettempdir()
    script_path = os.path.join(temp_dir, "chimera_docked_viz.py")
    safe_script_path = script_path.replace("\\", "/")

    with open(script_path, "w") as f:
        f.write(viz_script)

    for path in chimera_paths:
        if os.path.exists(path) or path == "chimera":
            try:
                command = f'"{path}" --script "{safe_script_path}"'
                subprocess.Popen(command, shell=True)
                print(f"✓ Chimera launched.")
                return True
            except Exception:
                continue

    print("[Chimera] ERROR: Could not launch Chimera")
    return False


# ============================
# Main Agent Run Endpoint
# ============================
@app.post("/api/agent/run")
def run_agent(request: AgentRequest):
    global rag_index, rag_texts, rag_metadata

    try:
        agent_steps.clear()

        question = request.question
        topic = extract_topic_nlp(question)

        add_step("thought", "Agent", f"Analyzing question for: {topic}")
        selected_tools = decide_tools(question)

        if openai_client:
            plan = generate_plan(question, selected_tools, openai_client)
            add_step("thought", "Reasoning", plan)

        pubmed_ids, pdb_ids, downloaded_files, cleaned_files, pdb_info = [], [], [], [], []
        compound_data, gene_id, docking_results, rag_results, chembl_data = None, None, [], [], []

        if "get_pubmed" in selected_tools:
            update_tool("pubmed")
            pubmed_ids = get_pubmed(topic)
            add_step("observation", "PubMed API", f"Found {len(pubmed_ids)} papers.")

        if "search_chembl" in selected_tools:
            update_tool("chembl")
            chembl_data = search_chembl(topic)

        if "search_pdb" in selected_tools:
            update_tool("pdb")
            pdb_ids = search_pdb(topic)
            if pdb_ids:
                downloaded_files = download_structures(pdb_ids)
                cleaned_files = clean_pdb_files(downloaded_files)
                pdb_info = [extract_pdb_info(f) for f in downloaded_files]
                add_step("observation", "PDB Cleaner", "Cleaned protein structures.")

        if "get_pubchem" in selected_tools:
            update_tool("pubchem")
            compound_data = get_pubchem(topic)
            if compound_data:
                add_step("observation", "PubChem API", f"Formula: {compound_data['formula']}")

        if "get_gene" in selected_tools:
            update_tool("ncbi")
            gene_id = get_gene(topic)

        if "run_docking" in selected_tools and cleaned_files:
            update_tool("docking", "active")
            add_step("action", "Docking Engine", f"Simulating {topic} docking...")

            dock_res, docked_ligand, receptor_pdbqt = run_docking_pipeline(topic, cleaned_files)
            docking_results = dock_res

            update_tool("docking", "idle")

            # Pass ORIGINAL PDB (with native HETATM cofactors) to Chimera for richer viz
            viz_receptor = downloaded_files[0] if downloaded_files else receptor_pdbqt

            # Detect Vina fallback vs. true success
            fallback_markers = ["error", "failed", "simulated", "pocket-placed", "base ligand"]
            vina_succeeded = bool(docking_results) and not any(
                any(kw in str(r).lower() for kw in fallback_markers)
                for r in docking_results
            )

            if viz_receptor and docked_ligand:
                if vina_succeeded:
                    add_step("observation", "Docking Engine", "Vina docking completed successfully.")
                else:
                    add_step("observation", "Docking Engine", "Vina search inconclusive — showing ligand placed in protein pocket.")
                open_chimera_docked_complex(viz_receptor, docked_ligand, topic)
            elif viz_receptor:
                add_step("observation", "Docking Engine", "Docking failed — displaying target protein only.")
                open_chimera_docked_complex(viz_receptor, "None", topic)
            else:
                add_step("observation", "Docking Engine", "Critical failure - missing target files.")

        if pubmed_ids:
            update_tool("rag")
            abstracts = fetch_pubmed_abstracts(pubmed_ids)
            if abstracts:
                rag_index, rag_texts, rag_metadata = create_vector_database(abstracts)
                rag_results = search_vector_database(question, rag_index, rag_texts, rag_metadata, top_k=3, year_filter=request.year_filter)

        collected_data = {
            "pubmed_abstracts": rag_results, "chembl_data": chembl_data, "compound_data": compound_data,
            "pdb_ids": pdb_ids, "docking_results": docking_results, "gene_id": gene_id, "pdb_info": pdb_info
        }

        answer = synthesize_answer(question, collected_data, openai_client) if openai_client else "API Error"
        add_step("answer", "Gemini AI", answer)

        report_file = generate_report(question, topic, answer, compound_data, gene_id, pdb_ids, pubmed_ids, downloaded_files, cleaned_files, pdb_info, rag_results, docking_results)

        return {
            "success": True, "topic": topic, "steps": agent_steps, "answer": answer,
            "docking_results": docking_results, "report_file": report_file, "rag_results": rag_results
        }

    except Exception as e:
        error_msg = traceback.format_exc()
        print("\n=== CRITICAL PYTHON ERROR ===")
        print(error_msg)
        return {
            "success": False,
            "topic": "Error",
            "steps": [{"type": "error", "tool": "System", "content": "Crash intercepted.", "timestamp": datetime.now().strftime("%H:%M:%S")}],
            "answer": f"**System Crash Detected!**\n\nHere is the exact Python error:\n```python\n{error_msg}\n```",
            "docking_results": [],
            "report_file": None,
            "rag_results": []
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)