import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.ingestion import ingest_pdf
from app.retriever import load_documents_from_chromadb, hybrid_search
from app.reranker import rerank_documents
from app.chain import generate_answer

import json

# Set up logging so we can see what's happening
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# This stores our documents in memory while the app is running
# So we don't reload from ChromaDB on every single request
app_state = {"documents": []}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This runs once when the app starts.
    We load all documents from ChromaDB into memory here
    so the retriever is ready immediately when requests come in.
    """
    logger.info("Starting RAG Research Assistant...")
    settings.vectorstore_dir.mkdir(parents=True, exist_ok=True)
    settings.pdf_dir.mkdir(parents=True, exist_ok=True)

    # Load existing documents from ChromaDB if any exist
    try:
        app_state["documents"] = load_documents_from_chromadb()
        logger.info(f"Loaded {len(app_state['documents'])} documents from ChromaDB")
    except Exception as e:
        logger.warning(f"No existing documents found: {e}")
        app_state["documents"] = []

    yield  # App runs here

    logger.info("Shutting down RAG Research Assistant...")


# Create the FastAPI app
app = FastAPI(
    title="RAG Research Assistant",
    description="Upload research papers and ask questions about them",
    version="1.0.0",
    lifespan=lifespan
)
# Set up Prometheus metrics
# This automatically tracks request count, latency, and errors
# and exposes them at /metrics endpoint
Instrumentator().instrument(app).expose(app)

# CORS middleware allows your React frontend to talk to this backend
# Without this, browsers block cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request/Response Models ───────────────────────────────────────────────

class QueryRequest(BaseModel):
    """What the frontend sends when asking a question"""
    question: str


class QueryResponse(BaseModel):
    """What we send back to the frontend"""
    answer: str
    sources: list
    chunks_used: int
    latency_ms: float


# ─── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """
    Simple endpoint to check if the app is running.
    Used by monitoring tools and Docker health checks.
    """
    return {
        "status": "healthy",
        "documents_loaded": len(app_state["documents"]),
        "version": "1.0.0"
    }

@app.get("/papers")
def list_papers():
    """
    Returns a list of all ingested papers from ChromaDB.
    Called by the frontend on startup to restore the papers list.
    """
    try:
        sources = set()
        for doc in app_state["documents"]:
            source = doc.metadata.get("source", "")
            if source:
                sources.add(source)

        papers = [{"name": name} for name in sorted(sources)]
        return {"papers": papers, "total": len(papers)}
    except Exception as e:
        return {"papers": [], "total": 0}

@app.post("/ingest")
async def ingest_endpoint(file: UploadFile = File(...)):
    """
    Upload a PDF and ingest it into ChromaDB.

    The frontend sends a PDF file here.
    We save it to disk then run the ingestion pipeline.
    """
    # Validate it's a PDF
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted"
        )

    logger.info(f"Received file: {file.filename}")

    # Save the uploaded file to disk
    settings.pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = settings.pdf_dir / file.filename

    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Run ingestion pipeline
    try:
        result = ingest_pdf(pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Reload documents into memory so new PDF is searchable immediately
    app_state["documents"] = load_documents_from_chromadb()
    logger.info(f"Reloaded {len(app_state['documents'])} documents after ingestion")

    return {
        "message": f"Successfully ingested {file.filename}",
        "chunks_created": result["chunks_created"],
        "total_documents": len(app_state["documents"])
    }


@app.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest):
    """
    Ask a question about the ingested research papers.

    The frontend sends a question here.
    We run the full RAG pipeline and return the answer.
    """
    if not app_state["documents"]:
        raise HTTPException(
            status_code=400,
            detail="No documents ingested yet. Please upload a PDF first."
        )

    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    logger.info(f"Received question: {request.question[:50]}...")

    # Track how long the full pipeline takes
    start_time = time.time()

    # Run the RAG pipeline
    retrieved = hybrid_search(request.question, app_state["documents"])
    reranked = rerank_documents(request.question, retrieved)
    result = generate_answer(request.question, reranked)

    latency_ms = (time.time() - start_time) * 1000
    logger.info(f"Query completed in {latency_ms:.0f}ms")

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        chunks_used=result["chunks_used"],
        latency_ms=round(latency_ms, 2)
    )
# ─── Model Versioning Endpoints ────────────────────────────────────────────

VERSIONS_DIR = Path("versions")


def load_version(version_name: str) -> dict:
    """Load a specific version config from disk."""
    version_file = VERSIONS_DIR / f"{version_name}.json"
    if not version_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Version '{version_name}' not found"
        )
    with open(version_file, "r") as f:
        return json.load(f)


def get_active_version_name() -> str:
    """Read which version is currently active."""
    active_file = VERSIONS_DIR / "active.json"
    if not active_file.exists():
        return "v1"
    with open(active_file, "r") as f:
        data = json.load(f)
    return data.get("active_version", "v1")


def set_active_version(version_name: str):
    """Write the active version to disk."""
    active_file = VERSIONS_DIR / "active.json"
    with open(active_file, "w") as f:
        json.dump({"active_version": version_name}, f, indent=2)


@app.get("/models/versions")
def list_versions():
    """
    List all available model versions.
    Returns all .json files in the versions/ directory
    except active.json.
    """
    if not VERSIONS_DIR.exists():
        return {"versions": [], "active_version": "v1"}

    versions = []
    for file in sorted(VERSIONS_DIR.glob("*.json")):
        if file.stem == "active":
            continue
        with open(file, "r") as f:
            data = json.load(f)
        versions.append({
            "version": data["version"],
            "description": data.get("description", ""),
            "created_at": data.get("created_at", ""),
        })

    active = get_active_version_name()
    return {"versions": versions, "active_version": active}


@app.get("/models/active")
def get_active_model():
    """
    Get the currently active model configuration.
    Shows exactly which models and settings are being used right now.
    """
    active_name = get_active_version_name()
    version_data = load_version(active_name)
    return {
        "active_version": active_name,
        "config": version_data["config"],
        "description": version_data.get("description", "")
    }


@app.post("/models/switch/{version_name}")
def switch_version(version_name: str):
    """
    Switch to a different model version.
    This is your rollback mechanism — if v2 breaks,
    call POST /models/switch/v1 to instantly roll back.
    """
    # Verify the version exists before switching
    version_data = load_version(version_name)

    # Update active.json
    set_active_version(version_name)

    logger.info(f"Switched to model version: {version_name}")

    return {
        "message": f"Successfully switched to {version_name}",
        "active_version": version_name,
        "config": version_data["config"],
        "description": version_data.get("description", "")
    }


@app.post("/models/save")
def save_version(
    version_name: str,
    description: str = "New version"
):
    """
    Save current settings as a new named version.
    Use this before making changes so you can roll back later.
    """
    VERSIONS_DIR.mkdir(exist_ok=True)

    version_data = {
        "version": version_name,
        "description": description,
        "created_at": str(Path("versions").stat().st_mtime),
        "config": {
            "embedding_model": settings.embedding_model,
            "rerank_model": settings.rerank_model,
            "chat_model": settings.chat_model,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "bm25_weight": settings.bm25_weight,
            "chroma_weight": settings.chroma_weight,
            "bm25_top_k": settings.bm25_top_k,
            "chroma_top_k": settings.chroma_top_k,
            "rerank_top_n": settings.rerank_top_n,
        }
    }

    version_file = VERSIONS_DIR / f"{version_name}.json"
    with open(version_file, "w") as f:
        json.dump(version_data, f, indent=2)

    logger.info(f"Saved new model version: {version_name}")

    return {
        "message": f"Version '{version_name}' saved successfully",
        "version": version_data
    }