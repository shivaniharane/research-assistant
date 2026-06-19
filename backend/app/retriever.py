import logging

from langchain_cohere import CohereEmbeddings
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny

from app.config import settings
from app.ingestion import CHILD_COLLECTION, PARENT_COLLECTION

logger = logging.getLogger(__name__)


def get_embedding_model() -> CohereEmbeddings:
    """Create Cohere embedding model."""
    return CohereEmbeddings(
        model=settings.embedding_model,
        cohere_api_key=settings.cohere_api_key,
    )


def get_qdrant_client() -> QdrantClient:
    """Create Qdrant client."""
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )


def load_child_documents() -> list[Document]:
    """
    Load all child chunks from Qdrant for BM25 indexing.
    Called once at app startup.
    """
    logger.info("Loading child chunks from Qdrant")

    client = get_qdrant_client()

    results = client.scroll(
        collection_name=CHILD_COLLECTION,
        limit=10000,
        with_payload=True,
        with_vectors=False,
    )

    documents = []
    for point in results[0]:
        page_content = point.payload.get("page_content", "")
        # Qdrant stores our metadata nested under a "metadata" key —
        # unwrap it here instead of flattening the whole payload.
        metadata = point.payload.get("metadata", {})
        documents.append(Document(
            page_content=page_content,
            metadata=metadata
        ))

    logger.info(f"Loaded {len(documents)} child chunks from Qdrant")
    return documents


def load_documents_from_chromadb() -> list[Document]:
    """Backwards compatible alias."""
    return load_child_documents()


def fetch_parent_chunks_batch(parent_ids: list[str]) -> list[Document]:
    """
    Fetch multiple parent chunks in ONE Qdrant call.
    Much faster than fetching one at a time.
    Uses Qdrant payload filtering to match parent_ids.
    """
    if not parent_ids:
        return []

    client = get_qdrant_client()

    results = client.scroll(
        collection_name=PARENT_COLLECTION,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="metadata.parent_id",
                    match=MatchAny(any=parent_ids)
                )
            ]
        ),
        limit=len(parent_ids) * 2,
        with_payload=True,
        with_vectors=False,
    )

    parents = []
    for point in results[0]:
        page_content = point.payload.get("page_content", "")
        # Same unwrap fix as above — metadata is nested.
        metadata = point.payload.get("metadata", {})
        parents.append(Document(
            page_content=page_content,
            metadata=metadata
        ))

    logger.info(f"Batch fetched {len(parents)} parent chunks")
    return parents


def hybrid_search(
    query: str,
    documents: list[Document]
) -> list[Document]:
    """
    Hierarchical hybrid search:
    1. BM25 keyword search on child chunks
    2. Qdrant semantic search on child chunks
    3. Collect unique parent IDs from matched children
    4. Batch fetch all parents in ONE Qdrant call
    5. Return parent chunks for LLM context
    """
    logger.info(f"Running hierarchical hybrid search for: {query}")

    embedding_model = get_embedding_model()

    # --- BM25 on child chunks ---
    bm25 = BM25Retriever.from_documents(documents)
    bm25.k = settings.bm25_top_k
    bm25_results = bm25.invoke(query)

    # --- Qdrant semantic search on child chunks ---
    child_store = QdrantVectorStore.from_existing_collection(
        embedding=embedding_model,
        collection_name=CHILD_COLLECTION,
        url=f"http://{settings.qdrant_host}:{settings.qdrant_port}",
    )
    qdrant_results = child_store.similarity_search(
        query, k=settings.qdrant_top_k
    )

    # --- Combine and deduplicate child results ---
    seen_content = set()
    combined_children = []

    for doc in qdrant_results + bm25_results:
        if doc.page_content not in seen_content:
            seen_content.add(doc.page_content)
            combined_children.append(doc)

    logger.info(f"Found {len(combined_children)} unique child chunks")

    # --- Collect unique parent IDs ---
    seen_parent_ids = []
    for child in combined_children:
        parent_id = child.metadata.get("parent_id")
        if parent_id and parent_id not in seen_parent_ids:
            seen_parent_ids.append(parent_id)

    # --- Batch fetch all parents in ONE call ---
    parent_docs = fetch_parent_chunks_batch(seen_parent_ids)

    if not parent_docs:
        logger.warning("Parent fetch returned nothing, using children")
        return combined_children

    return parent_docs