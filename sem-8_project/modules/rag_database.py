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
# Fetch PubMed abstracts with metadata
# ============================


def fetch_pubmed_abstracts(pubmed_ids):


    abstracts = []


    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


    for pid in pubmed_ids:


        params = {
            "db": "pubmed",
            "id": pid,
            "retmode": "xml",
            "rettype": "abstract"
        }


        try:
            response = requests.get(url, params=params, timeout=10)


            if response.status_code == 200:
                text = response.text


                # Extract title
                title = ""
                title_match = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", text, re.DOTALL)
                if title_match:
                    title = re.sub(r"<.*?>", "", title_match.group(1)).strip()


                # Extract abstract
                abstract = ""
                abstract_match = re.search(r"<AbstractText.*?>(.*?)</AbstractText>", text, re.DOTALL)
                if abstract_match:
                    abstract = re.sub(r"<.*?>", "", abstract_match.group(1)).strip()


                # Extract year
                year = ""
                year_match = re.search(r"<PubDate>.*?<Year>(.*?)</Year>", text, re.DOTALL)
                if year_match:
                    year = year_match.group(1).strip()


                # Extract journal
                journal = ""
                journal_match = re.search(r"<Title>(.*?)</Title>", text, re.DOTALL)
                if journal_match:
                    journal = re.sub(r"<.*?>", "", journal_match.group(1)).strip()


                # Extract authors
                authors = []
                author_matches = re.findall(r"<LastName>(.*?)</LastName>", text)
                for a in author_matches[:3]:
                    authors.append(a.strip())
                author_str = ", ".join(authors)
                if len(author_matches) > 3:
                    author_str += " et al."


                if abstract:
                    abstracts.append({
                        "id": pid,
                        "title": title,
                        "abstract": abstract,
                        "year": year,
                        "journal": journal,
                        "authors": author_str
                    })


        except Exception as e:
            print(f"[Warning] Could not fetch abstract for {pid}: {e}")
            continue


    return abstracts



# ============================
# Create vector database with metadata
# ============================


def create_vector_database(abstracts):


    texts = []
    metadata = []


    for item in abstracts:
        # Combine title + abstract for better embedding
        combined = f"{item['title']}. {item['abstract']}"
        texts.append(combined)
        metadata.append({
            "id": item["id"],
            "title": item["title"],
            "year": item["year"],
            "journal": item["journal"],
            "authors": item["authors"]
        })


    embeddings = model.encode(texts)
    embeddings = np.array(embeddings).astype("float32")


    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)


    return index, texts, metadata



# ============================
# Search vector database with filtering
# ============================


def search_vector_database(query, index, texts, metadata, top_k=3, year_filter=None):


    query_embedding = model.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")


    # Search more results to allow filtering
    distances, indices = index.search(query_embedding, top_k * 3)


    results = []


    for i, idx in enumerate(indices[0]):
        if idx >= len(texts):
            continue


        meta = metadata[idx]


        # Apply year filter if specified
        if year_filter and meta["year"]:
            try:
                if int(meta["year"]) < year_filter:
                    continue
            except:
                pass


        results.append({
            "text": texts[idx],
            "metadata": meta,
            "score": float(distances[0][i])
        })


        if len(results) >= top_k:
            break


    return results