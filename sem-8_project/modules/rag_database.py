import requests
import faiss
import numpy as np
import re
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

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                text = response.text.strip()
                abstracts.append({
                    "id": pid,
                    "abstract": text
                })

        except Exception as e:
            print(f"[Warning] Could not fetch abstract for {pid}: {e}")
            continue

    return abstracts


# ============================
# Create vector database
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

def search_vector_database(query, index, texts, top_k=3):

    query_embedding = model.encode([query])

    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = index.search(query_embedding, top_k)

    results = []

    for idx in indices[0]:
        results.append(texts[idx])

    return results


# ============================
# Clean PubMed text
# ============================

def clean_text(text):

    text = text.replace("\n", " ")

    text = re.sub(r"\d+\.", "", text)

    text = re.sub(r"\s+", " ", text)

    return text


# ============================
# Generate answer
# ============================

def generate_answer(question, results):

    print("\n=== Generated Scientific Answer ===\n")

    combined = ""

    for r in results:
        combined += " " + clean_text(r)

    sentences = combined.split(". ")

    filtered = []

    for s in sentences:

        s = s.strip()

        if any(x in s.lower() for x in [
            "doi",
            "author information",
            "department",
            "university",
            "journal",
            "online ahead",
            "collection",
            "contributed equally"
        ]):
            continue

        if len(s) > 60:
            filtered.append(s)

    summary = filtered[:4]

    for s in summary:
        print(s + ".")