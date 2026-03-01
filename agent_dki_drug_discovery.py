import requests
import os


# ============================
# PUBCHEM API
# ============================
def get_pubchem(compound):

    print("\n=== PUBCHEM ===")

    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound}/property/MolecularFormula,MolecularWeight/JSON"

    response = requests.get(url)

    if response.status_code == 200:

        data = response.json()
        props = data["PropertyTable"]["Properties"][0]

        print("Compound:", compound)
        print("Formula:", props["MolecularFormula"])
        print("Weight:", props["MolecularWeight"])

    else:
        print("Compound not found")


# ============================
# PUBMED API
# ============================
def get_pubmed(query):

    print("\n=== PUBMED ===")

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": 5
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:

        ids = response.json()["esearchresult"]["idlist"]

        for pid in ids:
            print("Paper ID:", pid)

    else:
        print("Error retrieving PubMed")


# ============================
# NCBI GENE API
# ============================
def get_ncbi_gene(gene):

    print("\n=== NCBI GENE ===")

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    params = {
        "db": "gene",
        "term": gene,
        "retmode": "json",
        "retmax": 1
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:

        ids = response.json()["esearchresult"]["idlist"]

        if ids:
            print("Gene:", gene)
            print("Gene ID:", ids[0])
        else:
            print("Gene not found")

    else:
        print("Error retrieving gene")


# ============================
# PDB SEARCH API
# ============================
def search_pdb(protein):

    print("\n=== PDB SEARCH ===")

    url = "https://search.rcsb.org/rcsbsearch/v2/query"

    query = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {
                "value": protein
            }
        },
        "return_type": "entry"
    }

    response = requests.post(url, json=query)

    pdb_ids = []

    if response.status_code == 200:

        data = response.json()

        if "result_set" in data:

            for item in data["result_set"][:5]:
                pdb_id = item["identifier"]
                pdb_ids.append(pdb_id)
                print("PDB ID:", pdb_id)

    else:
        print("Error retrieving PDB")

    return pdb_ids


# ============================
# DOWNLOAD PDB OR CIF FILES
# ============================
def download_pdb_files(pdb_ids):

    folder = "pdb_files"

    if not os.path.exists(folder):
        os.makedirs(folder)

    print("\n=== DOWNLOADING STRUCTURE FILES ===")

    for pdb_id in pdb_ids:

        pdb_url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
        cif_url = f"https://files.rcsb.org/download/{pdb_id}.cif"

        pdb_response = requests.get(pdb_url)

        if pdb_response.status_code == 200:

            filepath = os.path.join(folder, pdb_id + ".pdb")

            with open(filepath, "w") as f:
                f.write(pdb_response.text)

            print("Downloaded:", pdb_id, "(PDB)")

        else:

            cif_response = requests.get(cif_url)

            if cif_response.status_code == 200:

                filepath = os.path.join(folder, pdb_id + ".cif")

                with open(filepath, "w") as f:
                    f.write(cif_response.text)

                print("Downloaded:", pdb_id, "(CIF)")

            else:
                print("Not available:", pdb_id)


# ============================
# MAIN AGENT FUNCTION
# ============================
def run_agent():

    compound = "aspirin"
    gene = "BRCA1"
    protein = "EGFR"

    get_pubchem(compound)

    get_pubmed(compound)

    get_ncbi_gene(gene)

    pdb_ids = search_pdb(protein)

    download_pdb_files(pdb_ids)


# ============================
# ENTRY POINT
# ============================
if __name__ == "__main__":

    run_agent()