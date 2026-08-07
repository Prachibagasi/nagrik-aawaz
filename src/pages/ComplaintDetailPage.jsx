import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function ComplaintDetailPage() {
  const { id } = useParams()
  const { access, user } = useAuth()
  const [c, setC] = useState(null)
  const [sla, setSla] = useState(null)
  const [assignHint, setAssignHint] = useState(null)
  const [error, setError] = useState('')
  const [verifyMsg, setVerifyMsg] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await api(`/complaints/${id}/`, { token: access })
        if (!cancelled) setC(res)
      } catch (e) {
        if (!cancelled) setError(e.message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, access])

  useEffect(() => {
    let cancelled = false
    if (!id) return undefined
    ;(async () => {
      try {
        const s = await api(`/complaints/${id}/sla/`)
        if (!cancelled) setSla(s)
      } catch {
        if (!cancelled) setSla(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    let cancelled = false
    if (!id || !access || !user || (user.role !== 'officer' && user.role !== 'admin')) return undefined
    ;(async () => {
      try {
        const a = await api(`/complaints/${id}/assignment-suggestion/`, { token: access })
        if (!cancelled) setAssignHint(a)
      } catch {
        if (!cancelled) setAssignHint(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, access, user])

  async function verifyIssue() {
    setVerifyMsg('')
    try {
      const r = await api(`/complaints/${id}/verify/`, { method: 'POST', token: access })
      setVerifyMsg(
        r.already_verified ? 'You had already confirmed this report.' : 'Thanks — your confirmation was recorded.',
      )
      const detail = await api(`/complaints/${id}/`, { token: access })
      setC(detail)
    } catch (e) {
      setVerifyMsg(e.message || 'Could not verify')
    }
  }

  if (error) {
    return (
      <div className="container">
        <div className="error-banner">{error}</div>
        <Link to="/complaints">Back to list</Link>
      </div>
    )
  }

  if (!c) {
    return (
      <div className="container">
        <p className="muted">Loading…</p>
      </div>
    )
  }

  const ownerId = c.user_id
  const canVerify = user && ownerId && String(ownerId) !== String(user.id)

  return (
    <div className="container" style={{ maxWidth: 720 }}>
      <Link to="/complaints" className="muted" style={{ display: 'inline-block', marginBottom: 16 }}>
        ← My complaints
      </Link>
      <div className="glass-card">
        <div className="section-tag">Ticket</div>
        <h1 className="page-title" style={{ fontSize: 28 }}>
          {c.tracking_id}
        </h1>
        <p className="muted" style={{ marginBottom: 16 }}>
          Status: <span className={`status-pill ${c.status}`}>{c.status}</span>
          {c.category?.name ? ` · ${c.category.name}` : ''}
          {c.urgency_score != null ? ` · Urgency ${Number(c.urgency_score).toFixed(2)}` : ''}
          {c.sentiment_score != null ? ` · Sentiment ${Number(c.sentiment_score).toFixed(2)}` : ''}
          {c.verification_count != null && c.verification_count > 0
            ? ` · Community confirmations: ${c.verification_count}`
            : ''}
        </p>
        {sla ? (
          <>
            <div className="success-banner" style={{ marginBottom: 12 }}>
              Baseline SLA: {sla.message} Expected by <strong>{sla.expected_resolution_by}</strong>
              {sla.is_overdue ? ' — overdue vs baseline.' : ''}
            </div>
            {sla.phase2_prediction ? (
              <div className="glass-card" style={{ marginBottom: 16, padding: 16 }}>
                <strong>Phase 2 SLA prediction</strong>
                <p className="muted" style={{ marginTop: 8, lineHeight: 1.65 }}>
                  {sla.phase2_prediction.message} Confidence ~{(sla.phase2_prediction.confidence * 100).toFixed(0)}%.
                  Predicted window: <strong>{sla.phase2_prediction.predicted_calendar_days}</strong> calendar days (by{' '}
                  {sla.phase2_prediction.expected_resolution_by}).
                </p>
              </div>
            ) : null}
          </>
        ) : null}
        {c.cluster_key && (c.cluster_neighbor_count ?? 0) > 0 ? (
          <p style={{ marginBottom: 16 }}>
            <Link className="btn-secondary" style={{ display: 'inline-block', padding: '8px 14px' }} to={`/clusters/${encodeURIComponent(c.cluster_key)}`}>
              View duplicate cluster ({c.cluster_neighbor_count} related)
            </Link>
          </p>
        ) : null}
        {assignHint?.officer ? (
          <p className="muted" style={{ marginBottom: 16 }}>
            Suggested assignee: <strong>{assignHint.officer.full_name || assignHint.officer.phone}</strong> (open load{' '}
            {assignHint.open_assignment_load})
          </p>
        ) : null}
        {c.latitude != null && c.longitude != null ? (
          <p className="muted" style={{ marginBottom: 16 }}>
            <a
              href={`https://www.openstreetmap.org/?mlat=${c.latitude}&mlon=${c.longitude}#map=16/${c.latitude}/${c.longitude}`}
              target="_blank"
              rel="noreferrer"
              className="btn-secondary"
              style={{ display: 'inline-block', padding: '8px 14px' }}
            >
              Open map (OSM)
            </a>
          </p>
        ) : null}
        {c.extracted_locations?.length ? (
          <p className="muted" style={{ marginBottom: 16 }}>
            <strong>Speech / text locations:</strong> {c.extracted_locations.join(' · ')}
          </p>
        ) : null}
        <h3 style={{ marginBottom: 8 }}>Description</h3>
        <p style={{ marginBottom: 20, whiteSpace: 'pre-wrap' }}>{c.description}</p>
        {c.description_translated ? (
          <>
            <h3 style={{ marginBottom: 8 }}>Official-language stub (demo)</h3>
            <p className="muted" style={{ marginBottom: 20, whiteSpace: 'pre-wrap' }}>
              {c.description_translated}
            </p>
          </>
        ) : null}
        <h3 style={{ marginBottom: 8 }}>Location</h3>
        <p className="muted">
          {[c.address, c.ward, c.city, c.pincode].filter(Boolean).join(' · ') || '—'}
        </p>
        {canVerify ? (
          <div style={{ marginTop: 24 }}>
            <button type="button" className="btn-primary" onClick={verifyIssue}>
              Confirm issue on ground (community verification)
            </button>
            {verifyMsg ? (
              <p className="muted" style={{ marginTop: 10 }}>
                {verifyMsg}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}
