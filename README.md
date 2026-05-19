# 🔬 Research Paper Assistant

A production-ready AI-powered research paper assistant built with LLMOps principles.
Upload research papers and ask questions to instantly extract insights using
Retrieval-Augmented Generation (RAG).

---

## 🏗️ Architecture
User → React Frontend (port 5173)
│
▼
FastAPI Backend (port 8000)
│
┌──────┴──────┐
│             │
BM25      ChromaDB
(keyword)  (semantic)
│             │
└──────┬──────┘
│
Cohere Reranker
│
ChatCohere LLM
│
Answer
Monitoring:
Prometheus (port 9090) → scrapes /metrics
Grafana (port 3000)    → visualizes metrics

---

## 🧠 LLMOps Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | Cohere command-r-08-2024 | Answer generation |
| Embeddings | Cohere embed-english-v3.0 | Semantic search |
| Reranking | Cohere rerank-english-v3.0 | Result precision |
| Vector Store | ChromaDB | Semantic retrieval |
| Keyword Search | BM25 | Exact term matching |
| API Framework | FastAPI | Production API |
| Frontend | React + Vite | User interface |
| Containerization | Docker + Docker Compose | Deployment |
| Monitoring | Prometheus + Grafana | Performance tracking |
| Model Versioning | Custom JSON versioning | Rollback capability |

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- Cohere API key (free at https://cohere.com)

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd rag_research_assistant
```

### 2. Configure environment
```bash
cp backend/.env.example backend/.env
# Edit backend/.env and add your COHERE_API_KEY
```

### 3. Start everything with one command
```bash
docker-compose up --build
```

### 4. Access the application
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

---

## 📡 API Endpoints

### Core
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /papers | List ingested papers |
| POST | /ingest | Upload and ingest a PDF |
| POST | /query | Ask a question |

### Model Versioning
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /models/versions | List all versions |
| GET | /models/active | Get active config |
| POST | /models/switch/{version} | Switch version (rollback) |
| POST | /models/save | Save current config as version |

### Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /metrics | Prometheus metrics |

---

## 🔄 RAG Pipeline

PDF Upload
└── Extract text (pdfminer)
└── Split into chunks (RecursiveCharacterTextSplitter)
└── Generate embeddings (Cohere)
└── Store in ChromaDB
Query Processing
└── BM25 keyword search (top 2 chunks)
└── ChromaDB semantic search (top 5 chunks)
└── Hybrid fusion (weight: 30% BM25, 70% ChromaDB)
└── Cohere reranking (keep top 3)
└── ChatCohere generation
└── Return answer + sources + latency


---

## 🔁 Model Versioning & Rollback

Versions are stored as JSON files in `backend/versions/`.

```bash
# See all versions
GET http://localhost:8000/models/versions

# Check active version
GET http://localhost:8000/models/active

# Switch to v2 (experiment)
POST http://localhost:8000/models/switch/v2

# Roll back to v1 (stable)
POST http://localhost:8000/models/switch/v1

# Save current settings as new version
POST http://localhost:8000/models/save?version_name=v3&description=New+experiment
```

---

## 📊 Monitoring

Grafana dashboard at http://localhost:3000
- Username: `admin`
- Password: `admin123`

Metrics tracked:
- Requests per minute
- P95 response latency
- Total request count
- Error rate
- Per-endpoint breakdown

---

## 📁 Project Structure
rag_research_assistant/
├── backend/
│   ├── app/
│   │   ├── config.py        # Settings management
│   │   ├── ingestion.py     # PDF processing pipeline
│   │   ├── retriever.py     # Hybrid search (BM25 + ChromaDB)
│   │   ├── reranker.py      # Cohere reranking
│   │   ├── chain.py         # LLM answer generation
│   │   └── main.py          # FastAPI application
│   ├── versions/
│   │   ├── v1.json          # Stable configuration
│   │   ├── v2.json          # Experimental configuration
│   │   └── active.json      # Currently active version
│   ├── data/
│   │   ├── pdfs/            # Uploaded PDF files
│   │   └── vectorstore/     # ChromaDB persistent storage
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadPanel.jsx
│   │   │   ├── ChatPanel.jsx
│   │   │   └── StatsBar.jsx
│   │   ├── App.jsx
│   │   └── App.css
│   └── Dockerfile
├── monitoring/
│   └── prometheus.yml
├── docker-compose.yml
└── README.md

---

## 🛠️ Development (without Docker)

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| COHERE_API_KEY | required | Your Cohere API key |
| EMBEDDING_MODEL | embed-english-v3.0 | Cohere embedding model |
| RERANK_MODEL | rerank-english-v3.0 | Cohere reranking model |
| CHAT_MODEL | command-r-08-2024 | Cohere chat model |
| CHUNK_SIZE | 2048 | PDF chunk size |
| CHUNK_OVERLAP | 512 | Chunk overlap |
| BM25_WEIGHT | 0.3 | BM25 retriever weight |
| CHROMA_WEIGHT | 0.7 | ChromaDB retriever weight |
| LOG_LEVEL | INFO | Logging level |

---




