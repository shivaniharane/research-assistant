function StatsBar({ stats, uploadedFiles }) {
  return (
    <div className="stats-bar">

      <div className="stat-item">
        <svg className="stat-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        <span className="stat-value">{uploadedFiles.length}</span>
        <span className="stat-label">Papers</span>
      </div>

      <div className="stat-divider" />

      <div className="stat-item">
        <svg className="stat-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span className="stat-value">{stats.totalQueries}</span>
        <span className="stat-label">Queries</span>
      </div>

      <div className="stat-divider" />

      <div className="stat-item">
        <svg className="stat-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <span className="stat-value">{stats.lastLatency > 0 ? `${stats.lastLatency}ms` : "—"}</span>
        <span className="stat-label">Last response</span>
      </div>

      <div className="stat-divider" />

      <div className="stat-item">
        <svg className="stat-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        <span className="stat-value">{stats.avgLatency > 0 ? `${stats.avgLatency}ms` : "—"}</span>
        <span className="stat-label">Avg latency</span>
      </div>

      <div className="stat-divider" />

      <div className="stat-item">
        <svg className="stat-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        <span className="stat-value" style={{ color: "#16A34A" }}>Live</span>
        <span className="stat-label">Backend</span>
      </div>

      <span className="stats-version">RAG Research Assistant v1.0</span>
    </div>
  )
}

export default StatsBar