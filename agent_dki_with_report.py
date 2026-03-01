import requests
import os


# ============================
# PUBCHEM
# ============================
def get_pubchem(compound):

    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound}/property/MolecularFormula,MolecularWeight/JSON"

    response = requests.get(url)

    if response.status_code == 200:

        data = response.json()
        props = data["PropertyTable"]["Properties"][0]

        return {
            "compound": compound,
            "formula": props["MolecularFormula"],
            "weight": props["MolecularWeight"]
        }

    return None


# ============================
# PUBMED
# ============================
def get_pubmed(query):

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": 5
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:

        return response.json()["esearchresult"]["idlist"]

    return []


# ============================
# NCBI GENE
# ============================
def get_gene(gene):

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
            return ids[0]

    return None


# ============================
# SEARCH PDB
# ============================
def search_pdb(protein):

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
                pdb_ids.append(item["identifier"])

    return pdb_ids


# ============================
# DOWNLOAD STRUCTURES
# ============================
def download_structures(pdb_ids):

    folder = "pdb_files"

    if not os.path.exists(folder):
        os.makedirs(folder)

    downloaded = []

    for pdb_id in pdb_ids:

        pdb_url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
        cif_url = f"https://files.rcsb.org/download/{pdb_id}.cif"

        pdb_response = requests.get(pdb_url)

        if pdb_response.status_code == 200:

            path = os.path.join(folder, pdb_id + ".pdb")

            with open(path, "w") as f:
                f.write(pdb_response.text)

            downloaded.append(path)

        else:

            cif_response = requests.get(cif_url)

            if cif_response.status_code == 200:

                path = os.path.join(folder, pdb_id + ".cif")

                with open(path, "w") as f:
                    f.write(cif_response.text)

                downloaded.append(path)

    return downloaded


# ============================
# GENERATE REPORT
# ============================
def generate_report(compound_data, gene_id, pubmed_ids, pdb_ids, files):

    report = "Drug Discovery Agent Report\n"
    report += "===========================\n\n"

    report += "Compound Info:\n"
    if compound_data:
        report += f"Name: {compound_data['compound']}\n"
        report += f"Formula: {compound_data['formula']}\n"
        report += f"Weight: {compound_data['weight']}\n"
    report += "\n"

    report += "Gene Info:\n"
    report += f"Gene ID: {gene_id}\n\n"

    report += "PubMed Papers:\n"
    for pid in pubmed_ids:
        report += pid + "\n"
    report += "\n"

    report += "PDB Structures:\n"
    for pdb in pdb_ids:
        report += pdb + "\n"
    report += "\n"

    report += "Downloaded Files:\n"
    for file in files:
        report += file + "\n"

    with open("report.txt", "w") as f:
        f.write(report)

    print("\nReport saved as report.txt")


# ============================
# MAIN AGENT
# ============================
def run_agent():

    print("\n=== AgentDKI Drug Discovery Agent ===")

    compound = input("Enter compound name: ")
    gene = input("Enter gene name: ")
    protein = input("Enter protein name: ")

    compound_data = get_pubchem(compound)

    pubmed_ids = get_pubmed(compound)

    gene_id = get_gene(gene)

    pdb_ids = search_pdb(protein)

    files = download_structures(pdb_ids)

    generate_report(compound_data, gene_id, pubmed_ids, pdb_ids, files)


# ============================
# START
# ============================
if __name__ == "__main__":
    run_agent()