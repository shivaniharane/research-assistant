import logging
import time
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from app.config import settings
from app.ingestion import ingest_pdf
from app.retriever import load_child_documents, hybrid_search
from app.reranker import rerank_documents
from app.chain import generate_answer

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app_state = {"documents": []}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once at startup.
    Loads child chunks from Qdrant into memory for BM25 indexing.
    """
    logger.info("Starting RAG Research Assistant...")
    settings.pdf_dir.mkdir(parents=True, exist_ok=True)

    try:
        app_state["documents"] = load_child_documents()
        logger.info(
            f"Loaded {len(app_state['documents'])} "
            f"child chunks from Qdrant"
        )
    except Exception as e:
        logger.warning(f"Could not load documents at startup: {e}")
        app_state["documents"] = []

    yield

    logger.info("Shutting down RAG Research Assistant...")


app = FastAPI(
    title="RAG Research Assistant",
    description="Upload research papers and ask questions about them",
    version="2.0.0",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list
    chunks_used: int
    latency_ms: float


# ── Core endpoints ─────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "documents_loaded": len(app_state["documents"]),
        "version": "2.0.0",
        "database": "qdrant",
        "parser": "llamaparse"
    }


@app.get("/papers")
def list_papers():
    """List all ingested papers from child chunk metadata."""
    try:
        sources = set()
        for doc in app_state["documents"]:
            source = doc.metadata.get("source", "")
            if source:
                sources.add(source)
        papers = [{"name": name} for name in sorted(sources)]
        return {"papers": papers, "total": len(papers)}
    except Exception:
        return {"papers": [], "total": 0}


@app.post("/ingest")
async def ingest_endpoint(file: UploadFile = File(...)):
    """Upload a PDF and ingest it into Qdrant."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted"
        )

    logger.info(f"Received file: {file.filename}")

    settings.pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = settings.pdf_dir / file.filename

    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        result = ingest_pdf(pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Reload child chunks into memory for BM25
    app_state["documents"] = load_child_documents()
    logger.info(
        f"Reloaded {len(app_state['documents'])} "
        f"child chunks after ingestion"
    )

    return {
        "message": f"Successfully ingested {file.filename}",
        "parent_chunks": result["parent_chunks"],
        "child_chunks": result["child_chunks"],
        "total_documents": len(app_state["documents"]),
        "database": "qdrant",
        "parser": "llamaparse"
    }


@app.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest):
    """Ask a question about the ingested research papers."""
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

    start_time = time.time()

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


# ── Model versioning endpoints ─────────────────────────────────────────────

VERSIONS_DIR = Path("versions")


def load_version(version_name: str) -> dict:
    version_file = VERSIONS_DIR / f"{version_name}.json"
    if not version_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Version '{version_name}' not found"
        )
    with open(version_file, "r") as f:
        return json.load(f)


def get_active_version_name() -> str:
    active_file = VERSIONS_DIR / "active.json"
    if not active_file.exists():
        return "v1"
    with open(active_file, "r") as f:
        data = json.load(f)
    return data.get("active_version", "v1")


def set_active_version(version_name: str):
    active_file = VERSIONS_DIR / "active.json"
    with open(active_file, "w") as f:
        json.dump({"active_version": version_name}, f, indent=2)


@app.get("/models/versions")
def list_versions():
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

    return {"versions": versions, "active_version": get_active_version_name()}


@app.get("/models/active")
def get_active_model():
    active_name = get_active_version_name()
    version_data = load_version(active_name)
    return {
        "active_version": active_name,
        "config": version_data["config"],
        "description": version_data.get("description", "")
    }


@app.post("/models/switch/{version_name}")
def switch_version(version_name: str):
    version_data = load_version(version_name)
    set_active_version(version_name)
    logger.info(f"Switched to model version: {version_name}")
    return {
        "message": f"Successfully switched to {version_name}",
        "active_version": version_name,
        "config": version_data["config"],
        "description": version_data.get("description", "")
    }


@app.post("/models/save")
def save_version(version_name: str, description: str = "New version"):
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
            "bm25_top_k": settings.bm25_top_k,
            "qdrant_top_k": settings.qdrant_top_k,
            "qdrant_weight": settings.qdrant_weight,
            "bm25_weight": settings.bm25_weight,
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