from pydantic_settings import BaseSettings
from pathlib import Path

# This class automatically reads .env file when the app starts
class Settings(BaseSettings):
    
    # API Keys
    cohere_api_key: str

    # Storage Paths
    vectorstore_dir: Path = Path("data/vectorstore")
    pdf_dir: Path = Path("data/pdfs")

    # Model Names
    embedding_model: str = "embed-english-v3.0"
    rerank_model: str = "rerank-english-v3.0"
    chat_model: str = "command-r-plus"

    # Retrieval Settings
    chunk_size: int = 2048
    chunk_overlap: int = 512
    bm25_top_k: int = 2
    chroma_top_k: int = 5
    rerank_top_n: int = 3
    bm25_weight: float = 0.3
    chroma_weight: float = 0.7

    # App Settings
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# creates one single settings object that the whole app imports and uses
settings = Settings()