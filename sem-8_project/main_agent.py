import os
import nltk
from dotenv import load_dotenv
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.corpus import stopwords
from groq import Groq
from modules.pubmed_api import get_pubmed
from modules.pdb_api import search_pdb
from modules.pubchem_api import get_pubchem
from modules.ncbi_api import get_gene
from modules.downloader import download_structures
from modules.pdb_cleaner import clean_pdb_files, extract_pdb_info, clean_all_pdb_in_folder
from modules.tool_agent import decide_tools, generate_plan, synthesize_answer
from modules.report_generator import generate_report
from modules.docking import run_docking_pipeline
from modules.rag_database import (
    fetch_pubmed_abstracts,
    create_vector_database,
    search_vector_database
)

# ============================
# Load environment variables
# ============================

load_dotenv()

# ============================
# Download NLTK data (first time only)
# ============================

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("averaged_perceptron_tagger", quiet=True)
nltk.download("averaged_perceptron_tagger_eng", quiet=True)
nltk.download("stopwords", quiet=True)


# ============================
# NLP-based topic extraction using NLTK
# ============================

def extract_topic_nlp(question):
    tokens = word_tokenize(question)
    tagged = pos_tag(tokens)
    stop_words = set(stopwords.words("english"))
    generic = {
        "role", "effect", "use", "function", "discovery",
        "research", "study", "tell", "explain", "describe"
    }

    nouns = []
    for word, tag in tagged:
        if tag in ("NN", "NNP", "NNS", "NNPS"):
            if word.lower() not in stop_words and word.lower() not in generic:
                nouns.append(word)

    if nouns:
        return max(nouns, key=len)

    for word, tag in tagged:
        if word.lower() not in stop_words and word.isalpha():
            return word

    return question.split()[0]


# ============================
# Main Agent Loop
# ============================

def run_agent():

    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        print("ERROR: GROQ_API_KEY not found in .env file")
        return

    print("\nInitializing Groq AI...")
    groq_client = Groq(api_key=api_key)
    print("Groq AI ready.")

    print("\n" + "=" * 60)
    print("   AgentDKI Drug Discovery Research Assistant")
    print("   Powered by PubMed + PDB + PubChem + NCBI")
    print("   RAG + NLTK + Tool Calling + Groq AI")
    print("=" * 60)

    while True:

        question = input("\nAsk a biomedical question (type 'exit' to stop): ").strip()

        if question.lower() == "exit":
            print("Goodbye!")
            break

        if not question:
            print("Please enter a valid question.")
            continue

        print("\n" + "=" * 60)

        # ============================
        # Step 1: NLP Topic Extraction
        # ============================
        topic = extract_topic_nlp(question)
        print(f"[NLTK] Extracted search topic: '{topic}'")

        # ============================
        # Step 2: Tool Calling Logic
        # ============================
        selected_tools = decide_tools(question)
        print(f"\n[Tool Agent] Selected tools: {', '.join(selected_tools)}")

        # ============================
        # Step 3: Multi-Step Reasoning Plan
        # ============================
        print("\n[Tool Agent] Generating reasoning plan...")
        plan = generate_plan(question, selected_tools, groq_client)
        print("\n[Reasoning Plan]")
        print("-" * 60)
        print(plan)
        print("-" * 60)

        # ============================
        # Step 4: Execute Tools
        # ============================

        collected_data = {}
        pubmed_ids = []
        pdb_ids = []
        downloaded_files = []
        cleaned_files = []
        pdb_info = []
        compound_data = None
        gene_id = None
        docking_results = []

        # PubMed Search
        if "search_pubmed" in selected_tools:
            print(f"\n[PubMed] Searching for papers on: {topic}")
            pubmed_ids = get_pubmed(topic)
            if pubmed_ids:
                print(f"[PubMed] Found {len(pubmed_ids)} paper IDs:")
                for pid in pubmed_ids[:5]:
                    print(f"  - https://pubmed.ncbi.nlm.nih.gov/{pid}/")
            else:
                print("[PubMed] No papers found.")

        # PDB Search
        if "search_pdb" in selected_tools:
            print(f"\n[PDB] Searching protein structures for: {topic}")
            pdb_ids = search_pdb(topic)
            if pdb_ids:
                print(f"[PDB] Found {len(pdb_ids)} structures:")
                for pdb in pdb_ids:
                    print(f"  - https://www.rcsb.org/structure/{pdb}")

                # Download PDB files
                print("\n[PDB] Downloading structure files...")
                downloaded_files = download_structures(pdb_ids)
                print(f"[PDB] Downloaded {len(downloaded_files)} files:")
                for f in downloaded_files:
                    print(f"  - {f}")

                # Extract PDB info
                for f in downloaded_files:
                    info = extract_pdb_info(f)
                    pdb_info.append(info)
                    if info:
                        print(f"\n[PDB Info] {os.path.basename(f)}:")
                        print(f"  Protein : {info['protein_name']}")
                        print(f"  Chains  : {info['num_chains']}")
                        print(f"  Residues: {info['num_residues']}")
                        print(f"  Atoms   : {info['num_atoms']}")
            else:
                print("[PDB] No structures found.")

        # PDB Cleaning
        if "clean_pdb" in selected_tools and downloaded_files:
            print(f"\n[PDB Cleaner] Cleaning {len(downloaded_files)} PDB files...")
            cleaned_files = clean_pdb_files(downloaded_files)
            print(f"[PDB Cleaner] Cleaned {len(cleaned_files)} files.")

        # PubChem Search
        if "get_pubchem" in selected_tools:
            print(f"\n[PubChem] Fetching compound info for: {topic}")
            compound_data = get_pubchem(topic)
            if compound_data:
                print(f"[PubChem] Compound : {compound_data['compound']}")
                print(f"[PubChem] Formula  : {compound_data['formula']}")
                print(f"[PubChem] Weight   : {compound_data['weight']} g/mol")
            else:
                print("[PubChem] No compound data found.")

        # NCBI Gene Search
        if "get_gene" in selected_tools:
            print(f"\n[NCBI] Searching gene info for: {topic}")
            gene_id = get_gene(topic)
            if gene_id:
                print(f"[NCBI] Gene ID: {gene_id}")
                print(f"[NCBI] Link   : https://www.ncbi.nlm.nih.gov/gene/{gene_id}")
            else:
                print("[NCBI] No gene found.")

        # Docking Pipeline
        if "run_docking" in selected_tools and cleaned_files and compound_data:
            print(f"\n[Docking] Starting automated docking pipeline...")
            docking_results = run_docking_pipeline(topic, cleaned_files)
            if docking_results:
                print("\n[Docking] Results:")
                for dr in docking_results:
                    print(f"  - {dr}")

        # ============================
        # Step 5: RAG Pipeline
        # ============================
        rag_results = []

        if pubmed_ids:
            print(f"\n[RAG] Fetching abstracts for knowledge base...")
            abstracts = fetch_pubmed_abstracts(pubmed_ids)

            if abstracts:
                print(f"[RAG] Retrieved {len(abstracts)} abstracts with metadata.")
                print("[RAG] Building vector knowledge base...")
                index, texts, metadata = create_vector_database(abstracts)
                print(f"[RAG] Knowledge base ready with {index.ntotal} documents.")

                rag_results = search_vector_database(
                    question, index, texts, metadata, top_k=3
                )

                print("\n[RAG] Top Relevant Papers:")
                for i, r in enumerate(rag_results, 1):
                    meta = r["metadata"]
                    print(f"\n  Result {i}:")
                    print(f"  Title  : {meta['title']}")
                    print(f"  Authors: {meta['authors']}")
                    print(f"  Journal: {meta['journal']}")
                    print(f"  Year   : {meta['year']}")
                    print(f"  Link   : https://pubmed.ncbi.nlm.nih.gov/{meta['id']}/")
            else:
                print("[RAG] Could not retrieve abstracts.")

        # ============================
        # Step 6: Collect All Data
        # ============================
        collected_data = {
            "pubmed_abstracts": rag_results,
            "compound_data": compound_data,
            "gene_id": gene_id,
            "pdb_ids": pdb_ids,
            "pdb_info": pdb_info,
            "docking_results": docking_results
        }

        # ============================
        # Step 7: Synthesize Final Answer
        # ============================
        print("\n[Groq AI] Synthesizing final answer...\n")
        answer = synthesize_answer(question, collected_data, groq_client)

        print("=" * 60)
        print("SCIENTIFIC ANSWER")
        print("=" * 60)
        print(answer)
        print("=" * 60)

        # ============================
        # Step 8: Generate Report
        # ============================
        print("\n[Report] Generating full report...")
        report_file = generate_report(
            question=question,
            topic=topic,
            answer=answer,
            compound_data=compound_data,
            gene_id=gene_id,
            pdb_ids=pdb_ids,
            pubmed_ids=pubmed_ids,
            downloaded_files=downloaded_files,
            cleaned_files=cleaned_files,
            pdb_info=pdb_info,
            rag_results=rag_results,
            docking_results=docking_results
        )

        print(f"[Report] Full report saved to: {report_file}")
        print("\n" + "=" * 60)


if __name__ == "__main__":
    run_agent()