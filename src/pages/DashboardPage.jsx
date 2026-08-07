import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function DashboardPage() {
  const { user, access } = useAuth()
  const [stats, setStats] = useState(null)
  const [statsError, setStatsError] = useState('')

  const canStats = user && (user.role === 'officer' || user.role === 'admin')

  useEffect(() => {
    if (!canStats || !access) return
    let cancelled = false
    ;(async () => {
      try {
        const s = await api('/complaints/stats/', { token: access })
        if (!cancelled) setStats(s)
      } catch (e) {
        if (!cancelled) setStatsError(e.message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [canStats, access])

  return (
    <div className="container">
      <div className="section-tag">Overview</div>
      <h1 className="page-title">Welcome{user?.full_name ? `, ${user.full_name}` : ''}</h1>
      <p className="muted" style={{ marginBottom: 28 }}>
        Role: <strong style={{ color: 'var(--text-primary)' }}>{user?.role}</strong> · Phone {user?.phone}
      </p>

      <div className="grid-2" style={{ marginBottom: 28 }}>
        <Link to="/voice" className="glass-card" style={{ display: 'block' }}>
          <h3 style={{ marginBottom: 8 }}>Voice reporting</h3>
          <p className="muted">Upload or record audio → STT → complaint form (project highlight).</p>
        </Link>
        <Link to="/complaints/new" className="glass-card" style={{ display: 'block' }}>
          <h3 style={{ marginBottom: 8 }}>Typed / geo complaint</h3>
          <p className="muted">GPS reverse lookup, duplicate check, past resolutions, AI assist.</p>
        </Link>
        <Link to="/complaints" className="glass-card" style={{ display: 'block' }}>
          <h3 style={{ marginBottom: 8 }}>My complaints</h3>
          <p className="muted">Ticket IDs, SLA panel on detail, OpenStreetMap link when coordinates exist.</p>
        </Link>
        {(user?.role === 'officer' || user?.role === 'admin') && (
          <Link to="/desk" className="glass-card" style={{ display: 'block' }}>
            <h3 style={{ marginBottom: 8 }}>Operations desk</h3>
            <p className="muted">All complaints, filters, 15s auto-refresh, status workflow, admin assignment.</p>
          </Link>
        )}
      </div>

      {canStats ? (
        <div className="glass-card">
          <h3 style={{ marginBottom: 12 }}>Complaint statistics</h3>
          {statsError ? <div className="error-banner">{statsError}</div> : null}
          {stats ? (
            <div>
              <p style={{ marginBottom: 8 }}>
                <strong>Total:</strong> {stats.total}
              </p>
              <p className="muted" style={{ fontSize: 13 }}>
                By status: {JSON.stringify(stats.by_status || {})}
              </p>
            </div>
          ) : (
            !statsError && <p className="muted">Loading stats…</p>
          )}
        </div>
      ) : null}
    </div>
  )
}
