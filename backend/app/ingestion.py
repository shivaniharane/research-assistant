import logging
from pathlib import Path

from langchain_cohere import CohereEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from llama_parse import LlamaParse
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

logger = logging.getLogger(__name__)

CHILD_COLLECTION = "child_chunks"
PARENT_COLLECTION = "parent_chunks"


def get_qdrant_client() -> QdrantClient:
    """Create Qdrant client connection."""
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )


def get_embedding_model() -> CohereEmbeddings:
    """Create Cohere embedding model."""
    return CohereEmbeddings(
        model=settings.embedding_model,
        cohere_api_key=settings.cohere_api_key,
    )


def ensure_collections_exist(client: QdrantClient) -> None:
    """
    Create Qdrant collections if they do not exist.
    Child collection — small chunks, searched during retrieval.
    Parent collection — large chunks, fetched for LLM context.
    Both use 1024-dim Cohere embeddings with cosine similarity.
    """
    existing = [c.name for c in client.get_collections().collections]

    if CHILD_COLLECTION not in existing:
        client.create_collection(
            collection_name=CHILD_COLLECTION,
            vectors_config=VectorParams(
                size=1024,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Created Qdrant collection: {CHILD_COLLECTION}")

    if PARENT_COLLECTION not in existing:
        client.create_collection(
            collection_name=PARENT_COLLECTION,
            vectors_config=VectorParams(
                size=1024,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Created Qdrant collection: {PARENT_COLLECTION}")


def extract_text_with_llamaparse(pdf_path: Path) -> str:
    """Extract clean markdown text from PDF using LlamaParse."""
    logger.info(f"Extracting text from {pdf_path.name} using LlamaParse")

    parser = LlamaParse(
        api_key=settings.llama_parse_api_key,
        result_type="markdown",
        verbose=False,
    )

    documents = parser.load_data(str(pdf_path))
    full_text = "\n\n".join([doc.text for doc in documents])

    logger.info(f"Extracted {len(full_text)} characters from {pdf_path.name}")
    return full_text


def create_parent_chunks(text: str, source_name: str) -> list[Document]:
    """
    Create LARGE parent chunks — full sections.
    These are sent to the LLM for complete context.
    Size: 2000 chars, overlap: 200.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
    )

    chunks = splitter.split_text(text)

    parents = [
        Document(
            page_content=chunk,
            metadata={
                "source": source_name,
                "parent_id": f"{source_name}_parent_{i}",
                "chunk_type": "parent",
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
        )
        for i, chunk in enumerate(chunks)
    ]

    logger.info(f"Created {len(parents)} parent chunks from {source_name}")
    return parents


def create_child_chunks(parents: list[Document]) -> list[Document]:
    """
    Create SMALL child chunks from each parent.
    These are searched during retrieval.
    Each child stores parent_id to fetch its parent later.
    Size: 400 chars, overlap: 50.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    children = []
    for parent in parents:
        child_texts = splitter.split_text(parent.page_content)
        for j, child_text in enumerate(child_texts):
            children.append(
                Document(
                    page_content=child_text,
                    metadata={
                        "source": parent.metadata["source"],
                        "parent_id": parent.metadata["parent_id"],
                        "chunk_type": "child",
                        "child_index": j,
                    }
                )
            )

    logger.info(f"Created {len(children)} child chunks")
    return children


def store_in_qdrant(
    documents: list[Document],
    collection_name: str,
) -> None:
    """
    Store documents with embeddings in Qdrant.
    Used for both parent and child collections.
    """
    logger.info(
        f"Storing {len(documents)} docs in "
        f"Qdrant collection: {collection_name}"
    )

    client = get_qdrant_client()
    embedding_model = get_embedding_model()

    ensure_collections_exist(client)

    QdrantVectorStore.from_documents(
        documents=documents,
        embedding=embedding_model,
        collection_name=collection_name,
        url=f"http://{settings.qdrant_host}:{settings.qdrant_port}",
    )

    logger.info(f"Stored {len(documents)} docs in {collection_name}")


def ingest_pdf(pdf_path: Path) -> dict:
    """
    Full hierarchical ingestion pipeline:
    PDF → LlamaParse → parent chunks → child chunks
        → store both in Qdrant
    """
    # Step 1: Extract clean text
    text = extract_text_with_llamaparse(pdf_path)

    # Step 2: Create large parent chunks for LLM context
    parents = create_parent_chunks(text, source_name=pdf_path.name)

    # Step 3: Create small child chunks for retrieval
    children = create_child_chunks(parents)

    # Step 4: Store both in Qdrant
    store_in_qdrant(parents, PARENT_COLLECTION)
    store_in_qdrant(children, CHILD_COLLECTION)

    return {
        "filename": pdf_path.name,
        "parent_chunks": len(parents),
        "child_chunks": len(children),
        "status": "success",
        "parser": "llamaparse",
        "database": "qdrant"
    }