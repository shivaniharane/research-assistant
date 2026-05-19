import { useState } from "react"
import UploadPanel from "./components/UploadPanel"
import ChatPanel from "./components/ChatPanel"
import MonitoringPanel from "./components/MonitoringPanel"
import StatsBar from "./components/StatsBar"
import "./App.css"

function App() {
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [activeTab, setActiveTab] = useState("chat")
  const [stats, setStats] = useState({
    totalQueries: 0,
    avgLatency: 0,
    lastLatency: 0
  })

  const updateStats = (latencyMs) => {
    setStats(prev => {
      const newTotal = prev.totalQueries + 1
      const newAvg = ((prev.avgLatency * prev.totalQueries) + latencyMs) / newTotal
      return {
        totalQueries: newTotal,
        avgLatency: Math.round(newAvg),
        lastLatency: Math.round(latencyMs)
      }
    })
  }

  const totalChunks = uploadedFiles.reduce((acc, f) => {
    const n = parseInt(f.chunks)
    return acc + (isNaN(n) ? 0 : n)
  }, 0)

  return (
    <div className="app">

      {/* ── Header ── */}
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
            </svg>
          </div>
          <div className="header-text">
            <h1>Research Assistant</h1>
            <p>Powered by Cohere · ChromaDB · LangChain</p>
          </div>
        </div>
        <div className="header-right">
          <div className="status-pill">
            <div className="status-dot" />
            API connected
          </div>
          <div className="header-icon" title="Settings">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
            </svg>
          </div>
        </div>
      </header>

      {/* ── Tabs ── */}
      <div className="tabs-bar">
        <button
          className={`tab-btn ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => setActiveTab("chat")}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          Chat
        </button>
        <button
          className={`tab-btn ${activeTab === "monitoring" ? "active" : ""}`}
          onClick={() => setActiveTab("monitoring")}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          Monitoring
        </button>
      </div>

      {/* ── Main ── */}
      <main className="main-content">
        {activeTab === "chat" ? (
          <>
            <UploadPanel
              uploadedFiles={uploadedFiles}
              setUploadedFiles={setUploadedFiles}
              totalChunks={totalChunks}
            />
            <ChatPanel updateStats={updateStats} />
          </>
        ) : (
          <MonitoringPanel />
        )}
      </main>

      {/* ── Stats Bar ── */}
      <StatsBar stats={stats} uploadedFiles={uploadedFiles} />
    </div>
  )
}

export default App