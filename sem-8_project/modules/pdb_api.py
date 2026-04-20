import requests


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