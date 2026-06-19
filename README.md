# 🔬 AI Research Assistant

A production-ready AI-powered research assistant that lets you upload academic papers and ask questions in plain English — getting cited, accurate answers in seconds.

Built with a full LLMOps stack: hybrid retrieval, reranking, real-time monitoring, model versioning, and Docker deployment.

---

## 📸 Screenshots

### Chat Interface
![Chat Interface](assets/chat-screenshot.png)

### Monitoring Dashboard
![Monitoring Dashboard](assets/monitoring-screenshot.png)

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/shivaniharane/research-assistant.git
cd research-assistant

# 2. Add your Cohere API key
cp backend/.env.example backend/.env
# Edit backend/.env and set COHERE_API_KEY=your-key-here

# 3. Start everything with one command
docker-compose up --build
```

Open your browser:

| Service | URL |
|---------|-----|
| App | http://localhost:5173 |
| API Docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

---

## 🧠 What It Does

Upload any research paper (PDF) and ask questions like:
- *"What is the main contribution of this paper?"*
- *"Explain the methodology used."*
- *"What are the key findings and limitations?"*

The system retrieves the most relevant sections from the paper and generates a cited, accurate answer.

---

## 🏗️ Architecture

```
User (React UI)
     │
     ├── POST /ingest ──► PDF text extraction
     │                     ├── Text normalization
     │                     ├── Chunk splitting (2048 chars, 512 overlap)
     │                     ├── Cohere embeddings (embed-english-v3.0)
     │                     └── ChromaDB (persisted to disk)
     │
     └── POST /query ──► Hybrid Retrieval
                          ├── BM25 keyword search (top-2)
                          ├── ChromaDB semantic search (top-5)
                          └── RRF fusion (30% BM25 / 70% ChromaDB)
                               │
                               ▼
                          Cohere Reranker (top-3)
                               │
                               ▼
                          Cohere LLM (command-r-08-2024)
                               │
                               ▼
                          Answer + Sources + Latency

Observability:
  FastAPI /metrics ──► Prometheus ──► Grafana Dashboards
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite |
| Backend | FastAPI + Python |
| LLM | Cohere command-r-08-2024 |
| Embeddings | Cohere embed-english-v3.0 |
| Reranking | Cohere rerank-english-v3.0 |
| Vector Store | ChromaDB |
| Keyword Search | BM25 |
| Monitoring | Prometheus + Grafana |
| Containerization | Docker + Docker Compose |

---

## ⚙️ LLMOps Features

### Model Versioning and Rollback

```bash
# See all versions
GET http://localhost:8000/models/versions

# Switch to experimental config
POST http://localhost:8000/models/switch/v2

# Roll back to stable config
POST http://localhost:8000/models/switch/v1
```

### Real-time Monitoring
- Request rate and P95 latency tracked via Prometheus
- Grafana dashboards embedded directly in the app
- `/metrics` endpoint auto-instrumented with prometheus-fastapi-instrumentator
- Metrics refresh every 15 seconds

### One-command Deployment

```bash
docker-compose up --build
```

Starts 4 containers: backend, frontend, Prometheus, Grafana.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check + document count |
| GET | /papers | List all indexed papers |
| POST | /ingest | Upload and index a PDF |
| POST | /query | Ask a question |
| GET | /models/versions | List model versions |
| GET | /models/active | Get active configuration |
| POST | /models/switch/{version} | Switch version (rollback) |
| POST | /models/save | Save current config as version |
| GET | /metrics | Prometheus metrics |

---

## 📁 Project Structure

```
rag_research_assistant/
├── backend/
│   ├── app/
│   │   ├── config.py           # Environment-based settings
│   │   ├── ingestion.py        # PDF processing pipeline
│   │   ├── retriever.py        # Hybrid BM25 + ChromaDB search
│   │   ├── reranker.py         # Cohere reranking
│   │   ├── chain.py            # LLM answer generation
│   │   └── main.py             # FastAPI application + endpoints
│   ├── versions/
│   │   ├── v1.json             # Stable configuration
│   │   ├── v2.json             # Experimental configuration
│   │   └── active.json         # Currently active version pointer
│   ├── data/
│   │   ├── pdfs/               # Uploaded PDF files
│   │   └── vectorstore/        # ChromaDB persistent storage
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadPanel.jsx      # PDF upload + paper list
│   │   │   ├── ChatPanel.jsx        # Chat interface
│   │   │   ├── MonitoringPanel.jsx  # Live metrics dashboard
│   │   │   └── StatsBar.jsx         # Bottom metrics bar
│   │   ├── App.jsx
│   │   └── App.css
│   └── Dockerfile
├── monitoring/
│   └── prometheus.yml          # Prometheus scrape config
├── assets/
│   ├── chat-screenshot.png
│   └── monitoring-screenshot.png
├── docker-compose.yml
└── README.md
```

---

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| COHERE_API_KEY | required | Your Cohere API key |
| EMBEDDING_MODEL | embed-english-v3.0 | Cohere embedding model |
| RERANK_MODEL | rerank-english-v3.0 | Cohere reranking model |
| CHAT_MODEL | command-r-08-2024 | Cohere chat model |
| CHUNK_SIZE | 2048 | PDF chunk size in characters |
| CHUNK_OVERLAP | 512 | Overlap between chunks |
| BM25_WEIGHT | 0.3 | BM25 retriever weight |
| CHROMA_WEIGHT | 0.7 | ChromaDB retriever weight |

---

## 🏃 Running Without Docker

**Backend:**

```bash
cd backend
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

---

## 💡 Key Design Decisions

**Why hybrid retrieval?**
BM25 handles exact term matching (model names, metrics) while ChromaDB handles semantic similarity. Combining both consistently outperforms either alone.

**Why reranking?**
Initial retrieval prioritizes recall — it casts a wide net. Cohere's cross-encoder reranker then scores each candidate against the query jointly, dramatically improving precision.

**Why RAG over fine-tuning?**
RAG keeps the LLM general-purpose and retrieves context at query time. Fine-tuning would require retraining every time a new paper is added — impractical for a dynamic corpus.

---

## 👩‍💻 Author

Built by **Shivani Harane** as part of a research assistantship in the MS Computer Science program.

**Get in touch:** [LinkedIn](https://linkedin.com/in/shivaniharane) · [GitHub](https://github.com/shivaniharane)
