import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function MyComplaintsPage() {
  const { access } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [fetchDone, setFetchDone] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setFetchDone(false)
      try {
        const res = await api('/complaints/mine/', { token: access })
        if (!cancelled) setData(res)
      } catch (e) {
        if (!cancelled) setError(e.message)
      } finally {
        if (!cancelled) setFetchDone(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [access])

  const rows = data?.results || []
  const loaded = fetchDone

  return (
    <div className="container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div className="section-tag">Tickets</div>
          <h1 className="page-title">My complaints</h1>
        </div>
        <Link to="/complaints/new" className="btn-primary">
          New complaint
        </Link>
      </div>
      {error ? <div className="error-banner" style={{ marginTop: 20 }}>{error}</div> : null}
      {!error && !loaded ? <p className="muted" style={{ marginTop: 24 }}>Loading…</p> : null}
      {!error && loaded && rows.length === 0 ? (
        <div className="glass-card empty-complaints-card" style={{ marginTop: 24 }}>
          <img
            src="/branding/empty-state.png"
            alt=""
            className="empty-complaints-art"
            width={800}
            height={600}
            decoding="async"
          />
          <p className="muted" style={{ marginTop: 16, fontSize: 16, textAlign: 'center' }}>
            No complaints yet — your voice can fix the first issue.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
            <Link to="/complaints/new" className="btn-primary">
              New complaint
            </Link>
          </div>
        </div>
      ) : !error && loaded ? (
        <div className="table-wrap glass-card" style={{ marginTop: 20, padding: 0 }}>
          <table className="simple">
            <thead>
              <tr>
                <th>Tracking</th>
                <th>Title</th>
                <th>Status</th>
                <th>City</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/complaints/${c.id}`}>{c.tracking_id}</Link>
                  </td>
                  <td>{c.title || '—'}</td>
                  <td>
                    <span className={`status-pill ${c.status}`}>{c.status}</span>
                  </td>
                  <td>{c.city || '—'}</td>
                  <td className="muted">{c.updated_at?.slice(0, 10) || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}
