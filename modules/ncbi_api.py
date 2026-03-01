import requests


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