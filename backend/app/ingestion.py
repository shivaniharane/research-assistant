import logging

# modern Python way to handle file paths
from pathlib import Path

from langchain_chroma import Chroma
from langchain_cohere import CohereEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pdfminer.high_level import extract_text as extract_pdf_text

from app.config import settings

# This sets up logging so we can see what the app is doing
# Instead of print() statements, we use logger.info()
logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Step 1: Open a PDF and extract all its text.
    Handles spaced-out characters from certain PDF encodings.
    """
    import re
    logger.info(f"Extracting text from {pdf_path.name}")

    with open(pdf_path, "rb") as f:
        raw_text = extract_pdf_text(f)

    # Step 1: collapse newlines into spaces
    cleaned = " ".join(raw_text.split("\n"))

    # Step 2: detect if text has single-char spacing issue
    # Pattern: "a t t e n t i o n" — every char separated by space
    single_char_pattern = re.findall(r'\b[a-zA-Z] [a-zA-Z] [a-zA-Z]\b', cleaned)
    total_words = len(cleaned.split())

    if total_words > 0 and len(single_char_pattern) / total_words > 0.1:
        logger.info("Detected spaced-out character encoding — fixing...")
        # Only remove spaces that are between SINGLE characters
        # This preserves spaces between real words
        cleaned = re.sub(r'(?<!\w)([a-zA-Z]) (?=[a-zA-Z] )', r'\1', cleaned)
        cleaned = re.sub(r'(?<=[a-zA-Z]{1}) ([a-zA-Z])(?!\w)', r'\1', cleaned)

    # Step 3: collapse multiple spaces
    cleaned = re.sub(r' {2,}', ' ', cleaned).strip()

    logger.info(f"Extracted {len(cleaned)} characters")
    return cleaned


def split_into_chunks(text: str, source_name: str) -> list[Document]:
    """
    Step 2: Split long text into smaller overlapping chunks.
    Each chunk becomes a Document object with metadata.
    """
    logger.info(f"Splitting text into chunks")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks = splitter.split_text(text)

    # Wrap each chunk in a Document object
    # Document has two parts: the text content + metadata about where it came from
    documents = [
        Document(
            page_content=chunk,
            metadata={
                "source": source_name,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
        )
        for i, chunk in enumerate(chunks)
    ]

    logger.info(f"Created {len(documents)} chunks from {source_name}")
    return documents


def store_in_chromadb(documents: list[Document]) -> None:
    """
    Step 3: Convert chunks to embeddings and store in ChromaDB.
    """
    logger.info("Storing documents in ChromaDB")

    # Create the embedding model
    # This converts text into numbers (vectors) that capture meaning
    embedding_model = CohereEmbeddings(
        model=settings.embedding_model,
        cohere_api_key=settings.cohere_api_key,
    )

    # Store in ChromaDB
    # persist_directory means data is saved to disk, not lost when app restarts
    Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        persist_directory=str(settings.vectorstore_dir),
    )

    logger.info(f"Stored {len(documents)} chunks in ChromaDB")


def ingest_pdf(pdf_path: Path) -> dict:
    """
    Main function that runs all 3 steps together.
    This is what the API endpoint will call.
    """
    # Make sure storage folders exist
    settings.vectorstore_dir.mkdir(parents=True, exist_ok=True)

    # Run the 3 steps in order
    text = extract_text_from_pdf(pdf_path)
    documents = split_into_chunks(text, source_name=pdf_path.name)
    store_in_chromadb(documents)

    return {
        "filename": pdf_path.name,
        "chunks_created": len(documents),
        "status": "success"
    }