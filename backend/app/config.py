from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):

    # API Keys
    cohere_api_key: str
    llama_parse_api_key: str

    # Storage Paths
    pdf_dir: Path = Field(
        default=Path("data/pdfs"),
        description="Directory where uploaded PDF files are stored.",
    )

    # Qdrant settings
    qdrant_host: str = Field(default="qdrant")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="rag_research")

    # Model Names
    embedding_model: str = "embed-english-v3.0"
    rerank_model: str = "rerank-english-v3.0"
    chat_model: str = "command-r-08-2024"

    # Retrieval Settings
    chunk_size: int = 2000
    chunk_overlap: int = 200
    bm25_top_k: int = 2
    qdrant_top_k: int = 5
    rerank_top_n: int = 3
    bm25_weight: float = 0.3
    qdrant_weight: float = 0.7

    # App Settings
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()