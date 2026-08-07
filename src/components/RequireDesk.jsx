import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function RequireDesk() {
  const { user, loading, access } = useAuth()

  if (!access) {
    return <Navigate to="/login" replace />
  }

  if (loading) {
    return (
      <div className="container" style={{ paddingTop: 48 }}>
        <p className="muted">Loading…</p>
      </div>
    )
  }

  if (user?.role !== 'officer' && user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}
