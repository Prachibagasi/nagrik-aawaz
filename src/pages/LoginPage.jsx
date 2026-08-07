import { useState } from 'react'
import { Link, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import AuthWaveBridge from '../components/AuthWaveBridge'
import PhoneInput from '../components/PhoneInput'
import { isValidIndianMobile10, normalizeIndianPhone } from '../utils/phone'

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/dashboard'

  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (isAuthenticated) {
    return <Navigate to={from} replace />
  }

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    if (!isValidIndianMobile10(phone)) {
      setError('Enter a valid 10-digit Indian mobile number.')
      return
    }
    setBusy(true)
    try {
      await login(normalizeIndianPhone(phone), password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-auth page-auth--spacer">
      <div className="container auth-container">
        <div className="auth-shell auth-shell--wave">
          <aside className="auth-aside auth-aside--login" aria-hidden="true">
            <div className="auth-aside-bubbles" />
            <div className="auth-aside-overlay" />
            <div className="auth-aside-content">
              <p className="auth-aside-kicker">Welcome back</p>
              <p className="auth-aside-headline">Secure access to your civic workspace</p>
              <p className="auth-aside-sub">Track complaints, voice reports, and updates in one place.</p>
            </div>
          </aside>
          <AuthWaveBridge />
          <div className="auth-panel auth-panel--spacer">
            <div className="auth-panel-intro">
              <span className="auth-badge">Account</span>
              <h1 className="auth-panel-title">Log in</h1>
              <p className="muted auth-panel-lead">
                Use your registered 10-digit mobile number and password.
              </p>
            </div>
            <form className="auth-form auth-form--spacer" onSubmit={onSubmit}>
              {error ? <div className="error-banner">{error}</div> : null}
              <div className="field">
                <label htmlFor="phone">Mobile number</label>
                <PhoneInput id="phone" value={phone} onChange={setPhone} />
              </div>
              <div className="field">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  className="input input-auth-line"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>
              <div className="auth-pill-row">
                <button type="submit" className="btn-primary btn-pill auth-submit-primary" disabled={busy}>
                  {busy ? 'Signing in…' : 'Sign in'}
                </button>
                <Link to="/register" className="btn-secondary btn-pill auth-submit-secondary">
                  Register
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
