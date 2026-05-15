import requests


def search_pdb(protein):

    """
    Fetch high-quality protein structures from RCSB PDB
    using the best experimental resolution.

    Lower resolution value = better structure quality.
    """

    print(f"[PDB] Searching best-quality structures for: {protein}")

    url = "https://search.rcsb.org/rcsbsearch/v2/query"

    query = {

        "query": {

            "type": "group",

            "logical_operator": "and",

            "nodes": [

                # Main protein/drug keyword search
                {
                    "type": "terminal",
                    "service": "full_text",
                    "parameters": {
                        "value": protein
                    }
                },

                # Prefer experimentally solved structures
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "exptl.method",
                        "operator": "exact_match",
                        "value": "X-RAY DIFFRACTION"
                    }
                },

                # Excellent resolution filter
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_entry_info.resolution_combined",
                        "operator": "less_or_equal",
                        "value": 2.5
                    }
                }
            ]
        },

        "return_type": "entry",

        # Sort by BEST resolution first
        "request_options": {

            "paginate": {
                "start": 0,
                "rows": 10
            },

            "sort": [
                {
                    "sort_by": "rcsb_entry_info.resolution_combined",
                    "direction": "asc"
                }
            ]
        }
    }

    try:

        response = requests.post(url, json=query, timeout=20)

        pdb_ids = []

        if response.status_code == 200:

            data = response.json()

            if "result_set" in data:

                for item in data["result_set"]:

                    pdb_id = item["identifier"]

                    if pdb_id not in pdb_ids:
                        pdb_ids.append(pdb_id)

        # ============================
        # Fallback Search
        # ============================

        if not pdb_ids:

            print("[PDB] No excellent-resolution structures found.")
            print("[PDB] Running fallback search...")

            fallback_query = {
                "query": {
                    "type": "terminal",
                    "service": "full_text",
                    "parameters": {
                        "value": protein
                    }
                },
                "return_type": "entry"
            }

            response = requests.post(
                url,
                json=fallback_query,
                timeout=20
            )

            if response.status_code == 200:

                data = response.json()

                if "result_set" in data:

                    for item in data["result_set"][:5]:

                        pdb_id = item["identifier"]

                        if pdb_id not in pdb_ids:
                            pdb_ids.append(pdb_id)

        print(f"[PDB] Selected structures: {pdb_ids}")

        return pdb_ids

    except Exception as e:

        print(f"[PDB] Search error: {e}")

        return []