import requests


def search_chembl(query):
    """
    Searches the ChEMBL database for molecules and bioactivity data
    related to the query.
    """
    # Searching the molecule endpoint for matches
    url = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
    
    # We use 'icontains' for a flexible text search
    params = {
        "molecule_synonyms__molecule_synonym__icontains": query,
        "limit": 5
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            molecules = data.get("molecules", [])
            
            results = []
            for mol in molecules:
                results.append({
                    "chembl_id": mol.get("molecule_chembl_id"),
                    "name": mol.get("pref_name", "Unknown Name"),
                    "type": mol.get("molecule_type", "Unknown Type"),
                    "max_phase": mol.get("max_phase", 0) # Phase 4 means FDA approved
                })
            return results
        else:
            return []
            
    except Exception as e:
        print(f"[ChEMBL API] Error: {str(e)}")
        return []