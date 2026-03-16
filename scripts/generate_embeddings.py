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
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "postgres_docs_v10")
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


def get_existing_embedding_count(connection_url: str, collection_name: str) -> int:
    """Return the number of embeddings already stored for a collection."""
    import psycopg

    conn_str = connection_url.replace("postgresql+psycopg://", "postgresql://")
    query = """
        SELECT COUNT(*)
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON c.uuid = e.collection_id
        WHERE c.name = %s
    """
    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (collection_name,))
                row = cur.fetchone()
                return int(row[0]) if row else 0
    except Exception:
        # If tables do not exist yet, we should index normally.
        return 0


def main():
    existing = get_existing_embedding_count(DATABASE_URL, COLLECTION_NAME)
    if existing > 0:
        print(
            f"Collection '{COLLECTION_NAME}' already contains {existing} embeddings. "
            "Skipping re-indexing."
        )
        return

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
