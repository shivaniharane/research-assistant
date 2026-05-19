import { useState, useEffect, useRef } from "react"

const PROMETHEUS_URL = "http://localhost:9090"
const GRAFANA_URL = "http://localhost:3000"
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

function MetricCard({ label, value, sub, color }) {
  return (
    <div className="mon-card">
      <p className="mon-card-label">{label}</p>
      <p className="mon-card-value" style={color ? { color } : {}}>
        {value}
      </p>
      {sub && <p className="mon-card-sub">{sub}</p>}
    </div>
  )
}

function BarChart({ title, bars, color }) {
  const max = Math.max(...bars.map(b => b.value), 1)
  return (
    <div className="mon-chart-card">
      <p className="mon-chart-title">{title}</p>
      <div className="mon-chart-area">
        {bars.map((bar, i) => (
          <div key={i} className="mon-bar-wrap">
            <div
              className="mon-bar"
              style={{
                height: `${Math.max((bar.value / max) * 100, 4)}%`,
                background: color,
                opacity: 0.4 + (i / bars.length) * 0.6
              }}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

function PipelineCard({ icon, title, desc, value }) {
  return (
    <div className="mon-pipeline-card">
      <p className="mon-pipeline-name">{icon} {title}</p>
      <p className="mon-pipeline-desc">{desc}</p>
      <div className="mon-pipeline-stat">
        <span className="mon-pipeline-val">{value}</span>
        <span className="mon-pipeline-lbl">typical</span>
      </div>
    </div>
  )
}

export default function MonitoringPanel() {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [metrics, setMetrics] = useState({
    totalRequests: 0,
    avgLatency: 0,
    errorRate: 0,
    requestRate: [],
    latencyData: [],
  })
  const intervalRef = useRef(null)

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_URL}/health`)
      const data = await res.json()
      setHealth(data)
    } catch {
      setHealth(null)
    }
  }

  const queryPrometheus = async (query) => {
    try {
      const res = await fetch(
        `${PROMETHEUS_URL}/api/v1/query?query=${encodeURIComponent(query)}`
      )
      const data = await res.json()
      return data.data?.result || []
    } catch {
      return []
    }
  }

  const queryRange = async (query, minutes = 30) => {
    try {
      const end = Math.floor(Date.now() / 1000)
      const start = end - minutes * 60
      const res = await fetch(
        `${PROMETHEUS_URL}/api/v1/query_range?query=${encodeURIComponent(query)}&start=${start}&end=${end}&step=60`
      )
      const data = await res.json()
      return data.data?.result?.[0]?.values || []
    } catch {
      return []
    }
  }

  const fetchMetrics = async () => {
    const totalResult = await queryPrometheus("sum(http_requests_total)")
    const totalRequests = totalResult[0]
      ? Math.round(parseFloat(totalResult[0].value[1]))
      : 0

    const latencyResult = await queryPrometheus(
      "sum(rate(http_request_duration_seconds_sum[5m])) / sum(rate(http_request_duration_seconds_count[5m]))"
    )
    const avgLatency = latencyResult[0]
      ? Math.round(parseFloat(latencyResult[0].value[1]) * 1000)
      : 0

    const errorResult = await queryPrometheus(
      "sum(rate(http_requests_total{status=~'5..'}[5m])) / sum(rate(http_requests_total[5m])) * 100"
    )
    const errorRate = errorResult[0]
      ? parseFloat(parseFloat(errorResult[0].value[1]).toFixed(1))
      : 0

    const rateValues = await queryRange("sum(rate(http_requests_total[1m]))", 30)
    const requestRate = rateValues.slice(-20).map((v, i) => ({
      label: `${i}`,
      value: parseFloat(parseFloat(v[1]).toFixed(4))
    }))

    const latencyValues = await queryRange(
      "sum(rate(http_request_duration_seconds_sum[1m])) / sum(rate(http_request_duration_seconds_count[1m]))",
      30
    )
    const latencyData = latencyValues.slice(-20).map((v, i) => ({
      label: `${i}`,
      value: Math.round(parseFloat(v[1]) * 1000)
    }))

    setMetrics({ totalRequests, avgLatency, errorRate, requestRate, latencyData })
    setLoading(false)
  }

  useEffect(() => {
    fetchHealth()
    fetchMetrics()
    intervalRef.current = setInterval(() => {
      fetchHealth()
      fetchMetrics()
    }, 15000)
    return () => clearInterval(intervalRef.current)
  }, [])

  const emptyBars = Array(20).fill({ label: "", value: 0 })

  return (
    <div className="mon-panel">

      <div className="mon-header">
        <div>
          <h2 className="mon-title">System Monitoring</h2>
          <p className="mon-subtitle">Live metrics · refreshes every 15 seconds</p>
        </div>
        <a
          href={GRAFANA_URL}
          target="_blank"
          rel="noreferrer"
          className="grafana-link"
        >
          Open Grafana
        </a>
      </div>

      {loading ? (
        <div className="mon-loading">Loading metrics from Prometheus...</div>
      ) : (
        <div className="mon-content">

          <div className="mon-cards-grid">
            <MetricCard
              label="Total requests"
              value={metrics.totalRequests}
              sub="all time"
            />
            <MetricCard
              label="Avg latency"
              value={metrics.avgLatency > 0 ? `${metrics.avgLatency}ms` : "--"}
              sub="last 5 minutes"
            />
            <MetricCard
              label="Error rate"
              value={metrics.errorRate > 0 ? `${metrics.errorRate}%` : "0%"}
              sub="last 5 minutes"
              color={metrics.errorRate > 5 ? "#DC2626" : "#16A34A"}
            />
            <MetricCard
              label="Backend health"
              value={health ? "Healthy" : "Offline"}
              sub={health ? `${health.documents_loaded} docs loaded` : "Cannot reach API"}
              color={health ? "#16A34A" : "#DC2626"}
            />
          </div>

          <div className="mon-charts-grid">
            <BarChart
              title="Request rate -- last 30 min"
              bars={metrics.requestRate.length > 0 ? metrics.requestRate : emptyBars}
              color="#6366F1"
            />
            <BarChart
              title="Response latency (ms) -- last 30 min"
              bars={metrics.latencyData.length > 0 ? metrics.latencyData : emptyBars}
              color="#3B82F6"
            />
          </div>

          <p className="mon-section-title">Pipeline breakdown</p>
          <div className="mon-pipeline-grid">
            <PipelineCard
              icon="🔍"
              title="BM25 + ChromaDB retrieval"
              desc="Hybrid keyword + semantic search over indexed chunks"
              value="~200ms"
            />
            <PipelineCard
              icon="⚡"
              title="Cohere reranking"
              desc="Cross-encoder reranking of top retrieved chunks"
              value="~300ms"
            />
            <PipelineCard
              icon="🤖"
              title="LLM generation"
              desc="Cohere command-r-08-2024 answer generation"
              value="~1.2s"
            />
          </div>

          <p className="mon-section-title">Grafana dashboard</p>
          <div className="mon-grafana-card">
            <div className="mon-grafana-header">
              <span>Live Grafana dashboard</span>
              <a
                href={GRAFANA_URL}
                target="_blank"
                rel="noreferrer"
                className="grafana-link"
              >
                Open full screen
              </a>
            </div>
            <iframe
              src="http://localhost:3000/d/adtpjtd/research-assistant?orgId=1&from=now-1h&to=now&timezone=browser&kiosk&refresh=15s"
              className="mon-grafana-iframe"
              title="Grafana Dashboard"
              frameBorder="0"
            />
            <p className="mon-grafana-hint">
              If the dashboard appears blank, open Grafana at localhost:3000 and set up your dashboard there first.
            </p>
          </div>

        </div>
      )}

    </div>
  )
}
