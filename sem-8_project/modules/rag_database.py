import requests
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# ============================
# Load embedding model
# ============================
model = SentenceTransformer("all-MiniLM-L6-v2")


# ============================
# Fetch PubMed abstracts
# ============================
def fetch_pubmed_abstracts(pubmed_ids):

    abstracts = []

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    for pid in pubmed_ids:

        params = {
            "db": "pubmed",
            "id": pid,
            "retmode": "text",
            "rettype": "abstract"
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:

            text = response.text.strip()

            abstracts.append({
                "id": pid,
                "abstract": text
            })

    return abstracts


# ============================
# Create FAISS vector database
# ============================
def create_vector_database(abstracts):

    texts = [item["abstract"] for item in abstracts]

    embeddings = model.encode(texts)

    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)

    index.add(embeddings)

    return index, texts


# ============================
# Search vector database
# ============================
def search_vector_database(query, index, texts, top_k=2):

    query_embedding = model.encode([query])

    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = index.search(query_embedding, top_k)

    results = []

    for idx in indices[0]:
        results.append(texts[idx])

    return results