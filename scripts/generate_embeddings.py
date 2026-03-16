import json
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from tqdm import tqdm

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from .env")

INPUT_FILE = Path(__file__).parent / "postgres_rag_data_v8.json"
COLLECTION_NAME = "postgres_docs_v9"
BATCH_SIZE = 500


def load_chunks():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"File not found: {INPUT_FILE}")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def chunks_to_documents(chunks):
    documents = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk.get("embedding_text", chunk["content"]),
            metadata={
                "id": chunk["id"],
                "source": chunk["source"],
                "title": chunk["title"],
                "section": chunk.get("section", ""),
                "type": chunk["type"],
                "token_count": chunk["token_count"],
                "raw_content": chunk["content"],
            }
        )
        documents.append(doc)
    return documents


def main():
    print("Loading chunks...")
    chunks = load_chunks()
    print(f"{len(chunks)} chunks loaded.")

    print("Converting to LangChain Documents...")
    documents = chunks_to_documents(chunks)

    print("Initializing embedding model (text-embedding-3-large)...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=OPENAI_API_KEY,
    )

    print(f"Connecting to PostgreSQL (collection: {COLLECTION_NAME})...")
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=DATABASE_URL,
        use_jsonb=True,
    )

    total_docs = len(documents)
    print(f"Indexing {total_docs} documents in batches of {BATCH_SIZE}...")

    for i in tqdm(range(0, total_docs, BATCH_SIZE), desc="Indexing"):
        batch = documents[i:i + BATCH_SIZE]
        try:
            vectorstore.add_documents(batch)
        except Exception as e:
            tqdm.write(f"Batch {i} failed: {e}")

    print("\nDone. Vector store ready.")


if __name__ == "__main__":
    main()
