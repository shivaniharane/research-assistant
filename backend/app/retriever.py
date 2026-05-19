import logging
from pathlib import Path

from langchain_cohere import CohereEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


def get_embedding_model() -> CohereEmbeddings:
    """
    Creates the Cohere embedding model.
    Same model used during ingestion so vectors match.
    """
    return CohereEmbeddings(
        model=settings.embedding_model,
        cohere_api_key=settings.cohere_api_key,
    )


def load_documents_from_chromadb() -> list[Document]:
    """
    Loads all stored documents from ChromaDB.
    Needed to build BM25 which works in memory.
    """
    logger.info("Loading documents from ChromaDB")

    embedding_model = get_embedding_model()

    docsearch = Chroma(
        persist_directory=str(settings.vectorstore_dir),
        embedding_function=embedding_model,
    )

    result = docsearch.get()

    documents = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(result["documents"], result["metadatas"])
    ]

    logger.info(f"Loaded {len(documents)} documents from ChromaDB")
    return documents


def hybrid_search(query: str, documents: list[Document]) -> list[Document]:
    """
    Our own simple hybrid search combining BM25 + ChromaDB.

    How it works:
    - BM25 finds documents matching exact keywords
    - ChromaDB finds documents matching the meaning
    - We combine both result lists and remove duplicates
    """
    logger.info(f"Running hybrid search for: {query}")

    embedding_model = get_embedding_model()

    # --- BM25 keyword search ---
    bm25 = BM25Retriever.from_documents(documents)
    bm25.k = settings.bm25_top_k
    bm25_results = bm25.invoke(query)

    # --- ChromaDB semantic search ---
    docsearch = Chroma(
        persist_directory=str(settings.vectorstore_dir),
        embedding_function=embedding_model,
    )
    chroma_results = docsearch.similarity_search(
        query, k=settings.chroma_top_k
    )

    # --- Combine results, remove duplicates ---
    # We use page_content as a unique key to detect duplicates
    seen = set()
    combined = []

    # Add ChromaDB results first (higher weight)
    for doc in chroma_results:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            combined.append(doc)

    # Add BM25 results that aren't already included
    for doc in bm25_results:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            combined.append(doc)

    logger.info(f"Hybrid search returned {len(combined)} unique documents")
    return combined


def build_retriever():
    """
    Loads documents and returns a ready-to-use search function.
    This is called once when the app starts.
    """
    documents = load_documents_from_chromadb()

    def retriever(query: str) -> list[Document]:
        return hybrid_search(query, documents)

    logger.info("Retriever built successfully")
    return retriever