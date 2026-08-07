import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

const STATUS_OPTIONS = ['submitted', 'acknowledged', 'in_progress', 'resolved', 'closed', 'rejected']

export default function AdminDeskPage() {
  const { access, user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [city, setCity] = useState('')
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [officers, setOfficers] = useState([])
  const [tick, setTick] = useState(0)

  const load = useCallback(async () => {
    setError('')
    try {
      const q = new URLSearchParams()
      q.set('page', String(page))
      if (status) q.set('status', status)
      if (city.trim()) q.set('city', city.trim())
      if (search.trim()) q.set('search', search.trim())
      const data = await api(`/complaints/?${q.toString()}`, { token: access })
      setRows(data.results || [])
      setCount(data.count ?? 0)
    } catch (e) {
      setError(e.message)
    }
  }, [access, page, status, city, search])

  useEffect(() => {
    queueMicrotask(() => {
      void load()
    })
  }, [load, tick])

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 15000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (!isAdmin) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await api('/auth/users/', { token: access })
        const list = (data.results || []).filter((u) => u.role === 'officer' || u.role === 'admin')
        if (!cancelled) setOfficers(list)
      } catch {
        if (!cancelled) setOfficers([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isAdmin, access])

  async function patchStatus(id, newStatus, note = '') {
    await api(`/complaints/${id}/status/`, {
      method: 'PATCH',
      token: access,
      body: { status: newStatus, note },
    })
    setTick((t) => t + 1)
  }

  async function assignOfficer(id, officerId) {
    if (!officerId) return
    await api(`/complaints/${id}/assign/`, {
      method: 'POST',
      token: access,
      body: { officer_id: officerId },
    })
    setTick((t) => t + 1)
  }

  return (
    <div className="container">
      <div className="section-tag">Operations</div>
      <h1 className="page-title">Admin & officer desk</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        Live list (auto-refresh every 15s). Phase 2:{' '}
        <Link to="/insights/sentiment" style={{ fontWeight: 600 }}>
          sentiment trends
        </Link>
        . Filter, update status, assign staff.
      </p>

      <div className="glass-card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end' }}>
          <div className="field" style={{ marginBottom: 0, minWidth: 140 }}>
            <label>Status</label>
            <select className="select" value={status} onChange={(e) => { setPage(1); setStatus(e.target.value) }}>
              <option value="">All</option>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0, minWidth: 140 }}>
            <label>City contains</label>
            <input className="input" value={city} onChange={(e) => { setPage(1); setCity(e.target.value) }} placeholder="Pune" />
          </div>
          <div className="field" style={{ marginBottom: 0, flex: 1, minWidth: 180 }}>
            <label>Search description</label>
            <input className="input" value={search} onChange={(e) => { setPage(1); setSearch(e.target.value) }} placeholder="pothole, water…" />
          </div>
          <button type="button" className="btn-secondary" onClick={() => setTick((t) => t + 1)}>
            Refresh now
          </button>
        </div>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      <p className="muted" style={{ marginBottom: 12 }}>
        Total: <strong style={{ color: 'var(--text-primary)' }}>{count}</strong>
      </p>

      <div className="table-wrap glass-card" style={{ padding: 0 }}>
        <table className="simple">
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Status</th>
              <th>City</th>
              <th>Citizen</th>
              <th>Update</th>
              {isAdmin ? <th>Assign</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={isAdmin ? 6 : 5} className="muted" style={{ padding: 24 }}>
                  No rows (adjust filters or ensure backend has complaints).
                </td>
              </tr>
            ) : (
              rows.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/complaints/${c.id}`}>{c.tracking_id}</Link>
                  </td>
                  <td>
                    <span className={`status-pill ${c.status}`}>{c.status}</span>
                  </td>
                  <td>{c.city || '—'}</td>
                  <td className="muted">{c.user_name || '—'}</td>
                  <td>
                    <select
                      className="select"
                      style={{ minWidth: 130, fontSize: 13 }}
                      value={c.status}
                      onChange={(e) => patchStatus(c.id, e.target.value, 'Updated from desk')}
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  {isAdmin ? (
                    <td>
                      <select
                        className="select"
                        style={{ minWidth: 140, fontSize: 13 }}
                        defaultValue=""
                        onChange={(e) => {
                          assignOfficer(c.id, e.target.value)
                          e.target.value = ''
                        }}
                      >
                        <option value="" disabled>
                          Officer…
                        </option>
                        {officers.map((o) => (
                          <option key={o.id} value={o.id}>
                            {o.full_name || o.phone}
                          </option>
                        ))}
                      </select>
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
        <button type="button" className="btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
          Previous page
        </button>
        <button type="button" className="btn-ghost" disabled={rows.length < 20} onClick={() => setPage((p) => p + 1)}>
          Next page
        </button>
      </div>
    </div>
  )
}
