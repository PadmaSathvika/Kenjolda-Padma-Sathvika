import requests


# ==============================
# PUBCHEM API
# ==============================
def get_pubchem_compound(name):

    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/MolecularFormula,MolecularWeight/JSON"

    r = requests.get(url)

    if r.status_code == 200:
        data = r.json()
        props = data["PropertyTable"]["Properties"][0]

        print("\n=== PUBCHEM RESULT ===")
        print("Name:", name)
        print("Formula:", props["MolecularFormula"])
        print("Weight:", props["MolecularWeight"])

    else:
        print("PubChem error:", r.status_code)


# ==============================
# PUBMED API
# ==============================
def search_pubmed(term):

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    params = {
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": 3
    }

    r = requests.get(url, params=params)

    if r.status_code == 200:

        ids = r.json()["esearchresult"]["idlist"]

        print("\n=== PUBMED RESULTS ===")

        for pid in ids:
            print("PubMed ID:", pid)

    else:
        print("PubMed error:", r.status_code)


# ==============================
# NCBI GENE API
# ==============================
def search_gene(name):

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    params = {
        "db": "gene",
        "term": name,
        "retmode": "json",
        "retmax": 1
    }

    r = requests.get(url, params=params)

    if r.status_code == 200:

        ids = r.json()["esearchresult"]["idlist"]

        print("\n=== NCBI GENE RESULT ===")

        if ids:
            print("Gene ID:", ids[0])
        else:
            print("Gene not found")

    else:
        print("NCBI error:", r.status_code)


# ==============================
# PDB API (WORKING VERSION)
# ==============================
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

    r = requests.post(url, json=query)

    print("\n=== PDB RESULTS ===")

    if r.status_code == 200:

        data = r.json()

        if "result_set" in data:

            count = 0

            for item in data["result_set"]:
                print("PDB ID:", item["identifier"])
                count += 1

                if count == 5:
                    break

        else:
            print("No results found")

    else:
        print("PDB error:", r.status_code)


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":

    get_pubchem_compound("aspirin")

    search_pubmed("aspirin cancer")

    search_gene("BRCA1")

    search_pdb("EGFR")