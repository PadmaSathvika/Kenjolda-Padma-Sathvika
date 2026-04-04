import os
import sys
import json
import subprocess
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
# Get the exact folder this api.py file is in
current_folder = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_folder, ".env")

# Force it to load that specific .env file
load_dotenv(dotenv_path=env_path)

# Grab the key securely from the .env file
my_gemini_key = os.environ.get("GEMINI_API_KEY")

if my_gemini_key:
    print("✅ SUCCESS: Gemini API Key loaded securely from .env!")
else:
    print("❌ ERROR: Could not find GEMINI_API_KEY in .env! Please check your file.")

# We use the OpenAI client, but we trick it into talking to Google's Gemini servers!
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

class RAGSearchRequest(BaseModel):
    query: str

class CompoundSearchRequest(BaseModel):
    compound: str

def extract_topic_nlp(question):
    tokens = word_tokenize(question)
    tagged = pos_tag(tokens)
    stop_words = set(stopwords.words("english"))
    generic = {"role", "effect", "use", "function", "discovery", "research", "study", "tell", "explain", "describe"}
    nouns = [word for word, tag in tagged if tag.startswith("NN") and word.lower() not in stop_words and word.lower() not in generic]
    if nouns: return max(nouns, key=len)
    for word, tag in tagged:
        if word.lower() not in stop_words and word.isalpha(): return word
    return question.split()[0]

def add_step(step_type, tool, content):
    step = {"type": step_type, "tool": tool, "content": content, "timestamp": datetime.now().strftime("%H:%M:%S")}
    agent_steps.append(step)

def add_memory(memory_type, content):
    agent_memory.append({
        "type": memory_type,
        "content": content,
        "timestamp": datetime.now().strftime("%H:%M %p")
    })

def update_tool(tool_name, status="active"):
    if tool_name in tool_stats:
        tool_stats[tool_name]["calls"] += 1
        tool_stats[tool_name]["status"] = status
        tool_stats[tool_name]["last_used"] = datetime.now().strftime("%H:%M:%S")

def open_pymol(pdb_file):
    pymol_paths = [r"C:\Program Files\PyMOL\PyMOL\PyMOL.exe", r"C:\Program Files (x86)\PyMOL\PyMOL\PyMOL.exe", "pymol"]
    for path in pymol_paths:
        try:
            subprocess.Popen([path, pdb_file])
            return True
        except FileNotFoundError: continue
    return False

# ============================
# Main Agent Run Endpoint 
# ============================
@app.post("/api/agent/run")
def run_agent(request: AgentRequest):
    global rag_index, rag_texts, rag_metadata
    agent_steps.clear()

    question = request.question
    topic = extract_topic_nlp(question)

    add_step("thought", "Agent", f"Analyzing question to find drug candidates related to: {topic}")
    selected_tools = decide_tools(question)
    add_step("thought", "Tool Agent", f"Selected tools: {', '.join(selected_tools)}")

    if openai_client:
        plan = generate_plan(question, selected_tools, openai_client)
        add_step("thought", "Reasoning", plan)

    pubmed_ids, pdb_ids, downloaded_files, cleaned_files, pdb_info = [], [], [], [], []
    compound_data, gene_id, docking_results, rag_results, chembl_data = None, None, [], [], []

    if "search_pubmed" in selected_tools:
        update_tool("pubmed")
        pubmed_ids = get_pubmed(topic)
        add_step("observation", "PubMed API", f"Found {len(pubmed_ids)} papers on {topic}")
        add_memory("short-term", f"PubMed returned {len(pubmed_ids)} papers for {topic}")

    if "search_chembl" in selected_tools:
        update_tool("chembl")
        add_step("action", "ChEMBL API", f"Searching ChEMBL database for: {topic}")
        chembl_data = search_chembl(topic)
        if chembl_data:
            add_step("observation", "ChEMBL API", f"Found {len(chembl_data)} related compounds in ChEMBL.")
            add_memory("short-term", f"ChEMBL retrieved {len(chembl_data)} compounds for {topic}")

    if "search_pdb" in selected_tools:
        update_tool("pdb")
        pdb_ids = search_pdb(topic)
        if pdb_ids:
            downloaded_files = download_structures(pdb_ids)
            pdb_info = [extract_pdb_info(f) for f in downloaded_files]
            cleaned_files = clean_pdb_files(downloaded_files)
            add_step("observation", "PDB Cleaner", f"Cleaned {len(cleaned_files)} files successfully")

    if "get_pubchem" in selected_tools:
        update_tool("pubchem")
        compound_data = get_pubchem(topic)
        if compound_data: add_step("observation", "PubChem API", f"Formula: {compound_data['formula']}")

    if "get_gene" in selected_tools:
        update_tool("ncbi")
        gene_id = get_gene(topic)
        if gene_id: add_step("observation", "NCBI API", f"Gene ID: {gene_id}")

    if "run_docking" in selected_tools and cleaned_files and compound_data:
        update_tool("docking", "active")
        add_step("action", "Docking Engine", f"Running molecular docking simulation for {topic}...")
        docking_results = run_docking_pipeline(topic, cleaned_files)
        update_tool("docking", "idle")
        if docking_results: add_step("observation", "Docking Engine", f"Docking completed.")
        if cleaned_files: open_pymol(cleaned_files[0])

    if pubmed_ids:
        update_tool("rag")
        abstracts = fetch_pubmed_abstracts(pubmed_ids)
        if abstracts:
            rag_index, rag_texts, rag_metadata = create_vector_database(abstracts)
            rag_results = search_vector_database(question, rag_index, rag_texts, rag_metadata, top_k=3, year_filter=request.year_filter)
            add_step("observation", "RAG Pipeline", f"Retrieved {len(rag_results)} relevant abstracts")
            add_memory("short-term", f"RAG retrieved {len(rag_results)} relevant abstracts for: {question}")

    collected_data = {
        "pubmed_abstracts": rag_results, "chembl_data": chembl_data, "compound_data": compound_data,
        "gene_id": gene_id, "pdb_ids": pdb_ids, "pdb_info": pdb_info, "docking_results": docking_results
    }

    answer = ""
    if openai_client:
        update_tool("openai") 
        answer = synthesize_answer(question, collected_data, openai_client)
        add_step("answer", "Gemini AI", answer)
        add_memory("short-term", f"Generated answer for: {question}")

    report_file = generate_report(question, topic, answer, compound_data, gene_id, pdb_ids, pubmed_ids, downloaded_files, cleaned_files, pdb_info, rag_results, docking_results)

    return {
        "success": True, "topic": topic, "steps": agent_steps, "answer": answer,
        "chembl_data": chembl_data, "compound_data": compound_data, "gene_id": gene_id, "pdb_ids": pdb_ids,
        "rag_results": [{"text": r["text"][:400], "metadata": r["metadata"]} for r in rag_results],
        "docking_results": docking_results, "report_file": report_file,
        "memory": agent_memory[-5:]
    }

@app.get("/api/tools/status")
def get_tool_status():
    total_calls = sum(t["calls"] for t in tool_stats.values())
    active_tools = sum(1 for t in tool_stats.values() if t["status"] == "active")
    return {
        "total_calls": total_calls,
        "active_tools": f"{active_tools}/{len(tool_stats)}",
        "tools": [{"name": name, "status": info["status"], "calls": info["calls"], "last_used": info["last_used"]} for name, info in tool_stats.items()]
    }

@app.get("/api/compounds/search")
def compound_search(name: str):
    return {"compound": get_pubchem(name), "pdb_ids": search_pdb(name), "gene_id": get_gene(name), "chembl_data": search_chembl(name)}

@app.get("/api/memory")
def get_memory():
    return {"total_items": len(agent_memory), "memory": agent_memory}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)