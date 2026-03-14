from modules.pubmed_api import get_pubmed
from modules.rag_database import (
    fetch_pubmed_abstracts,
    create_vector_database,
    search_vector_database,
    generate_answer
)


def extract_topic(question):

    stopwords = {
        "how", "what", "why", "when", "does",
        "do", "is", "are", "the", "a", "an"
    }

    words = question.lower().split()

    for word in words:
        if word not in stopwords:
            return word

    return words[0]


def run_agent():

    print("\n=== AgentDKI Biomedical Research Assistant ===")

    while True:

        question = input("\nAsk a biomedical question (type 'exit' to stop): ")

        if question.lower() == "exit":
            break

        topic = extract_topic(question)

        print("\nSearching PubMed for:", topic)

        pubmed_ids = get_pubmed(topic)

        if len(pubmed_ids) == 0:
            print("No papers found.")
            continue

        abstracts = fetch_pubmed_abstracts(pubmed_ids)

        if len(abstracts) == 0:
            print("No abstracts retrieved.")
            continue

        print("\nBuilding knowledge base...")

        index, texts = create_vector_database(abstracts)

        print("Knowledge base ready.")

        results = search_vector_database(question, index, texts)

        print("\nMost relevant research abstracts:\n")

        for i, r in enumerate(results, 1):
            print(f"\nResult {i}:\n")
            print(r[:500])

        generate_answer(question, results)


if __name__ == "__main__":
    run_agent()