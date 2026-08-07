import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function SentimentAnalyticsPage() {
  const { access } = useAuth()
  const [days, setDays] = useState(21)
  const [series, setSeries] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setError('')
      try {
        const res = await api(`/complaints/analytics/sentiment/?days=${days}`, { token: access })
        if (!cancelled) setSeries(res.series || [])
      } catch (e) {
        if (!cancelled) setError(e.message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [access, days])

  const minS = series.length ? Math.min(...series.map((s) => s.avg_sentiment)) : 0
  const maxS = series.length ? Math.max(...series.map((s) => s.avg_sentiment)) : 1

  return (
    <div className="container">
      <Link to="/desk" className="muted" style={{ display: 'inline-block', marginBottom: 16 }}>
        ← Desk
      </Link>
      <div className="section-tag">Phase 2 · Analytics</div>
      <h1 className="page-title">Sentiment trend</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        Average heuristic sentiment of new complaints per day (production baseline before swapping in a transformer
        model).
      </p>
      <div className="field" style={{ maxWidth: 220 }}>
        <label>Window (days)</label>
        <select className="select" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={14}>14</option>
          <option value={21}>21</option>
          <option value={30}>30</option>
          <option value={60}>60</option>
          <option value={90}>90</option>
        </select>
      </div>
      {error ? <div className="error-banner">{error}</div> : null}
      <div className="glass-card" style={{ marginTop: 20 }}>
        {series.length === 0 ? (
          <p className="muted">No scored complaints in this window yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {series.map((row) => {
              const span = maxS - minS || 1
              const pct = ((row.avg_sentiment - minS) / span) * 100
              return (
                <div key={row.date}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span>{row.date}</span>
                    <span>
                      n={row.count} · avg {row.avg_sentiment}
                    </span>
                  </div>
                  <div
                    style={{
                      height: 8,
                      borderRadius: 4,
                      background: 'var(--bg-tertiary)',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${pct}%`,
                        height: '100%',
                        background: 'var(--accent-primary)',
                        opacity: 0.65 + row.count * 0.02,
                        maxWidth: '100%',
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
