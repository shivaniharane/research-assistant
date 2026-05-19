import logging

from langchain_cohere import CohereRerank
from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


def rerank_documents(query: str, documents: list[Document]) -> list[Document]:
    """
    Takes retrieved documents and re-scores them against
    the query using Cohere's reranking model.

    Why reranking?
    Hybrid search is fast but approximate.
    Reranking is slower but much more precise.
    We use both together for best results.

    Args:
        query:     The user's question
        documents: Chunks from hybrid search

    Returns:
        Top N most relevant documents, sorted by relevance score
    """
    if not documents:
        logger.warning("No documents to rerank")
        return []

    logger.info(f"Reranking {len(documents)} documents")

    # Initialize Cohere reranker
    reranker = CohereRerank(
        model=settings.rerank_model,
        cohere_api_key=settings.cohere_api_key,
        top_n=settings.rerank_top_n,
    )

    # Rerank the documents
    # compress_documents scores each doc against the query
    # and returns only the top_n most relevant ones
    reranked = reranker.compress_documents(
        documents=documents,
        query=query
    )

    logger.info(f"Reranking complete. Kept {len(reranked)} documents")

    # Log relevance scores so we can see how confident the model is
    for i, doc in enumerate(reranked):
        score = doc.metadata.get("relevance_score", "N/A")
        source = doc.metadata.get("source", "unknown")
        logger.info(f"  [{i+1}] score={score:.4f} source={source}")

    return reranked