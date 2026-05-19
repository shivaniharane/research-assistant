import { useState, useEffect } from "react"
import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

function UploadPanel({ uploadedFiles, setUploadedFiles, totalChunks }) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [search, setSearch] = useState("")

  useEffect(() => {
    const fetchPapers = async () => {
      try {
        const response = await axios.get(`${API_URL}/papers`)
        const papers = response.data.papers.map(p => ({
          name: p.name,
          chunks: "indexed"
        }))
        setUploadedFiles(papers)
      } catch (err) {
        console.error("Could not fetch papers:", err)
      }
    }
    fetchPapers()
  }, [])

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    if (!file.name.endsWith(".pdf")) {
      setError("Only PDF files are accepted")
      return
    }
    setUploading(true)
    setError("")
    setSuccess("")
    const formData = new FormData()
    formData.append("file", file)
    try {
      const response = await axios.post(`${API_URL}/ingest`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      })
      setUploadedFiles(prev => {
        const exists = prev.find(f => f.name === file.name)
        if (exists) return prev
        return [...prev, {
          name: file.name,
          chunks: response.data.chunks_created
        }]
      })
      setSuccess("Indexed successfully")
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed")
    } finally {
      setUploading(false)
      e.target.value = ""
    }
  }

  const filtered = uploadedFiles.filter(f =>
    f.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="upload-panel">

      {/* Upload section */}
      <div className="sb-section">
        <p className="sb-label">Upload</p>
        <label className={`upload-btn ${uploading ? "disabled" : ""}`}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          {uploading ? "Indexing..." : "Upload PDF"}
          <input type="file" accept=".pdf" onChange={handleFileUpload} disabled={uploading} style={{ display: "none" }} />
        </label>
        <p className="upload-hint">PDF format · max 50MB</p>
        {success && <div className="msg success">✓ {success}</div>}
        {error && <div className="msg error">✗ {error}</div>}
      </div>

      {/* Search section */}
      <div className="sb-section">
        <p className="sb-label">Papers ({uploadedFiles.length})</p>
        <div className="search-box">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input
            type="text"
            placeholder="Search papers..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Papers list */}
      <div className="papers-list-section">
        {filtered.length === 0 ? (
          <div className="empty-msg">
            <span className="empty-icon">📂</span>
            {search ? "No papers match your search" : "Upload a PDF to get started"}
          </div>
        ) : (
          filtered.map((file, index) => (
            <div key={index} className="paper-item">
              <svg className="paper-file-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <span className="paper-name">{file.name.replace(".pdf", "")}</span>
              <span className="paper-chunks">{file.chunks}</span>
            </div>
          ))
        )}
      </div>

      {/* Stats grid */}
      <div className="sb-stats">
        <div className="mini-stat">
          <div className="mini-stat-val">{uploadedFiles.length}</div>
          <div className="mini-stat-lbl">Papers</div>
        </div>
        <div className="mini-stat">
          <div className="mini-stat-val">{totalChunks}</div>
          <div className="mini-stat-lbl">Chunks</div>
        </div>
      </div>

      {/* Model badge */}
      <div className="model-badge">
        <div className="model-badge-label">Active pipeline</div>
        <div className="model-badge-name">command-r-08-2024</div>
      </div>

    </div>
  )
}

export default UploadPanel