import requests


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