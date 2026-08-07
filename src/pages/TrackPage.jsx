import { useState } from 'react'
import { api } from '../api/client'

export default function TrackPage() {
  const [tid, setTid] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setResult(null)
    const id = tid.trim()
    if (!id) return
    setBusy(true)
    try {
      const path = `/complaints/track/${encodeURIComponent(id)}/`
      const data = await api(path)
      setResult(data)
    } catch (err) {
      setError(err.message || 'Not found')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container" style={{ maxWidth: 560 }}>
      <div className="section-tag">Public</div>
      <h1 className="page-title">Track complaint</h1>
      <p className="muted" style={{ marginBottom: 24 }}>Enter the tracking ID you received (for example NA-12345678).</p>
      <form className="glass-card" onSubmit={onSubmit}>
        {error ? <div className="error-banner">{error}</div> : null}
        <div className="field">
          <label htmlFor="track">Tracking ID</label>
          <input id="track" className="input" value={tid} onChange={(e) => setTid(e.target.value)} placeholder="NA-00000000" />
        </div>
        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={busy}>
          {busy ? 'Searching…' : 'Track'}
        </button>
      </form>
      {result ? (
        <div className="glass-card" style={{ marginTop: 20 }}>
          <h3 style={{ marginBottom: 8 }}>{result.tracking_id}</h3>
          <p className="muted" style={{ marginBottom: 12 }}>
            Status: <span className={`status-pill ${result.status}`}>{result.status}</span>
            {result.category ? ` · ${result.category}` : ''} · {result.city || '—'}
          </p>
          <h4 style={{ marginBottom: 8, fontSize: 14 }}>History</h4>
          <ul style={{ listStyle: 'none' }}>
            {(result.status_history || []).map((h, i) => (
              <li key={i} className="muted" style={{ marginBottom: 6, fontSize: 14 }}>
                <strong style={{ color: 'var(--text-primary)' }}>{h.status}</strong> — {h.note || '—'} ·{' '}
                {h.date?.slice(0, 19)?.replace('T', ' ') || ''}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
