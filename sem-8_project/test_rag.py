from modules.pubmed_api import get_pubmed
from modules.rag_database import (
    fetch_pubmed_abstracts,
    create_vector_database,
    search_vector_database
)


print("Fetching PubMed IDs...")

ids = get_pubmed("aspirin")

print("IDs:", ids)


print("\nFetching abstracts...")

abstracts = fetch_pubmed_abstracts(ids)


print("\nFirst abstract ID:")
print(abstracts[0]["id"])


print("\nFirst abstract preview:")
print(abstracts[0]["abstract"][:300])


print("\nCreating vector database...")

index, texts = create_vector_database(abstracts)


print("Vector database created successfully")
print("Total stored documents:", index.ntotal)


# ============================
# NEW PART: Semantic search
# ============================
print("\nSearching database...")

results = search_vector_database(
    "aspirin treatment",
    index,
    texts
)


print("\nTop result preview:")
print(results[0][:300])