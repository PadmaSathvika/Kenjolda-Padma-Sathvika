from modules.pubchem_api import get_pubchem
from modules.pubmed_api import get_pubmed
from modules.ncbi_api import get_gene
from modules.pdb_api import search_pdb
from modules.downloader import download_structures
from modules.report_generator import generate_report

# NEW: RAG imports
from modules.rag_database import (
    fetch_pubmed_abstracts,
    create_vector_database,
    search_vector_database
)


def run_agent():

    print("\n=== AgentDKI Drug Discovery Agent ===")

    compound = input("Enter compound name: ")
    gene = input("Enter gene name: ")
    protein = input("Enter protein name: ")

    print("\nRetrieving PubChem data...")
    compound_data = get_pubchem(compound)

    print("Retrieving PubMed papers...")
    pubmed_ids = get_pubmed(compound)

    print("Retrieving Gene info...")
    gene_id = get_gene(gene)

    print("Searching PDB structures...")
    pdb_ids = search_pdb(protein)

    print("Downloading structures...")
    files = download_structures(pdb_ids)

    # ============================
    # NEW: RAG workflow
    # ============================
    print("Fetching PubMed abstracts...")
    abstracts = fetch_pubmed_abstracts(pubmed_ids)

    print("Creating knowledge database...")
    index, texts = create_vector_database(abstracts)

    print("Finding most relevant research...")
    rag_results = search_vector_database(
        compound + " treatment",
        index,
        texts
    )

    print("\nMost relevant research preview:")
    print(rag_results[0][:300])

    # ============================
    # Generate report
    # ============================
    print("\nGenerating report...")
    generate_report(compound_data, gene_id, pubmed_ids, pdb_ids, files)

    print("\nDone. Report saved as report.txt")


if __name__ == "__main__":
    run_agent()