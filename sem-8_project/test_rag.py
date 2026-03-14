from modules.pubmed_api import get_pubmed
from modules.rag_database import (
    fetch_pubmed_abstracts,
    create_vector_database,
    search_vector_database,
    generate_answer
)


print("Fetching PubMed IDs...")

ids = get_pubmed("aspirin")

print("IDs:", ids)


print("\nFetching abstracts...")

abstracts = fetch_pubmed_abstracts(ids)


print("\nCreating vector database...")

index, texts = create_vector_database(abstracts)

print("Vector database created successfully")
print("Total stored documents:", index.ntotal)


# ============================
# NLP QUESTION SYSTEM
# ============================

print("\n=== Biomedical Question System ===")

while True:

    question = input("\nAsk a biomedical question (type 'exit' to stop): ")

    if question.lower() == "exit":
        break

    results = search_vector_database(question, index, texts)

    print("\nMost relevant research abstracts:\n")

    for i, r in enumerate(results, 1):

        print(f"\nResult {i}:\n")
        print(r[:500])

    generate_answer(question, results)