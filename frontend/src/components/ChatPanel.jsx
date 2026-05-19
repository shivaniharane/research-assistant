import { useState, useRef, useEffect } from "react"
import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

const SUGGESTED_PROMPTS = [
  { icon: "🎯", text: "What is the main contribution of this paper?" },
  { icon: "🔬", text: "Summarize the methodology used." },
  { icon: "📊", text: "What are the key findings and results?" },
  { icon: "⚠️", text: "What limitations does this paper acknowledge?" },
  { icon: "🏗️", text: "Explain the architecture proposed." },
  { icon: "📚", text: "Compare this with previous work." },
]

function ChatPanel({ updateStats }) {
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleAsk = async (q) => {
    const userQuestion = (q || question).trim()
    if (!userQuestion || loading) return
    setQuestion("")
    setLoading(true)
    setMessages(prev => [...prev, { role: "user", content: userQuestion }])
    try {
      const response = await axios.post(`${API_URL}/query`, { question: userQuestion })
      const data = response.data
      setMessages(prev => [...prev, {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        latency_ms: data.latency_ms
      }])
      updateStats(data.latency_ms)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || "Something went wrong. Please try again."
      setMessages(prev => [...prev, {
        role: "assistant",
        content: errorMsg,
        isError: true
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleAsk()
    }
  }

  const isEmpty = messages.length === 0 && !loading

  return (
    <div className="chat-panel">

      {isEmpty ? (
        <div className="messages">
          <div className="empty-state">
            <div className="empty-state-icon">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>
            </div>
            <h3>Ask anything about your research</h3>
            <p>Upload papers and instantly extract insights, methodologies, findings, and limitations.</p>
            <div className="suggested-prompts">
              {SUGGESTED_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  className="prompt-chip"
                  onClick={() => handleAsk(prompt.text)}
                >
                  <span className="prompt-icon">{prompt.icon}</span>
                  {prompt.text}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role} ${msg.isError ? "error" : ""}`}>
              <p className="msg-label">
                {msg.role === "user" ? "You" : "Assistant"}
              </p>

              {msg.role === "assistant" ? (
                <div className="ai-row">
                  <div className="ai-avatar">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div className={`bubble ${msg.isError ? "error" : ""}`}>
                      {msg.content}
                    </div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="sources">
                        <p className="sources-label">Sources</p>
                        {msg.sources.map((src, i) => (
                          <span key={i} className="source-tag">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                            {src.filename.replace(".pdf", "")}
                          </span>
                        ))}
                        <span className="latency-tag">⚡ {Math.round(msg.latency_ms)}ms</span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="bubble">{msg.content}</div>
              )}
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <p className="msg-label">Assistant</p>
              <div className="ai-row">
                <div className="ai-avatar">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                </div>
                <div className="bubble loading">
                  <span /><span /><span />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input */}
      <div className="input-wrapper">
        <div className="input-area">
          <textarea
            ref={inputRef}
            className="question-input"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your research papers..."
            rows={2}
            disabled={loading}
          />
          <span className="kbd-hint">↵ send</span>
          <button
            className="send-btn"
            onClick={() => handleAsk()}
            disabled={loading || !question.trim()}
            aria-label="Send message"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
          </button>
        </div>
      </div>

    </div>
  )
}

export default ChatPanel