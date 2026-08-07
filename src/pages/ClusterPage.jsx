import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function ClusterPage() {
  const { clusterKey } = useParams()
  const { access } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const path = `/complaints/clusters/${encodeURIComponent(clusterKey)}/`
        const res = await api(path, { token: access })
        if (!cancelled) setData(res)
      } catch (e) {
        if (!cancelled) setError(e.message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [clusterKey, access])

  if (error) {
    return (
      <div className="container">
        <div className="error-banner">{error}</div>
        <Link to="/complaints">Back</Link>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="container">
        <p className="muted">Loading cluster…</p>
      </div>
    )
  }

  return (
    <div className="container">
      <Link to="/complaints" className="muted" style={{ display: 'inline-block', marginBottom: 16 }}>
        ← My complaints
      </Link>
      <div className="section-tag">Phase 2 · Duplicate cluster</div>
      <h1 className="page-title">Related reports</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        Same geography + similar opening text bucket (<code>{clusterKey.slice(0, 12)}…</code>) · {data.count}{' '}
        ticket(s)
      </p>
      <div className="table-wrap">
        <table className="simple">
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>City</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(data.complaints || []).map((row) => (
              <tr key={row.id}>
                <td>{row.tracking_id}</td>
                <td>
                  <span className={`status-pill ${row.status}`}>{row.status}</span>
                </td>
                <td>{row.city || '—'}</td>
                <td>
                  <Link to={`/complaints/${row.id}`}>Open</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
