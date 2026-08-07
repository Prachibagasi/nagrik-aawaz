import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function RequireAuth() {
  const { access, loading } = useAuth()

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

  return <Outlet />
}
