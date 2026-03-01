import requests


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