import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'
import AuthWaveBridge from '../components/AuthWaveBridge'
import PhoneInput from '../components/PhoneInput'
import LanguageSelect from '../components/LanguageSelect'
import { digitsOnlyPhoneInput, isValidIndianMobile10, normalizeIndianPhone, validateEmailFormat } from '../utils/phone'

export default function RegisterPage() {
  const { register, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    phone: '',
    full_name: '',
    email: '',
    password: '',
    confirm_password: '',
    preferred_language: 'hi',
    otp: '',
  })
  const [otpSent, setOtpSent] = useState(false)
  const [devOtp, setDevOtp] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)
  const [otpBusy, setOtpBusy] = useState(false)

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }))
  }

  async function sendOtp() {
    setError('')
    setInfo('')
    if (!isValidIndianMobile10(form.phone)) {
      setError('Enter a valid 10-digit mobile number first.')
      return
    }
    setOtpBusy(true)
    try {
      const phone = normalizeIndianPhone(form.phone)
      const data = await api('/auth/otp/send/', { method: 'POST', body: { phone } })
      setOtpSent(true)
      setInfo(data.message || 'OTP sent.')
      if (data.dev_otp) {
        setDevOtp(String(data.dev_otp))
        setForm((f) => ({ ...f, otp: String(data.dev_otp) }))
      }
    } catch (err) {
      setError(err.message || 'Could not send OTP')
    } finally {
      setOtpBusy(false)
    }
  }

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setInfo('')
    if (!isValidIndianMobile10(form.phone)) {
      setError('Enter a valid 10-digit Indian mobile number.')
      return
    }
    if (!otpSent || !form.otp.trim()) {
      setError('Verify your mobile — tap Send OTP and enter the code.')
      return
    }
    try {
      if (form.email.trim()) validateEmailFormat(form.email)
    } catch (err) {
      setError(err.message)
      return
    }
    setBusy(true)
    try {
      const body = {
        phone: normalizeIndianPhone(form.phone),
        full_name: form.full_name.trim(),
        password: form.password,
        confirm_password: form.confirm_password,
        preferred_language: form.preferred_language,
        role: 'citizen',
        otp: form.otp.trim(),
      }
      if (form.email.trim()) body.email = validateEmailFormat(form.email)
      await register(body)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-auth page-auth--spacer page-auth--register">
      <div className="container auth-container">
        <div className="auth-shell auth-shell--wave auth-shell--wide">
          <aside className="auth-aside auth-aside--register" aria-hidden="true">
            <div className="auth-aside-bubbles" />
            <div className="auth-aside-overlay" />
            <div className="auth-aside-content">
              <p className="auth-aside-kicker">Citizen sign-up</p>
              <p className="auth-aside-headline">Your city deserves a clear voice</p>
              <p className="auth-aside-sub">Create an account to file and track civic issues with transparency.</p>
            </div>
          </aside>
          <AuthWaveBridge />
          <div className="auth-panel auth-panel--spacer">
            <div className="auth-panel-intro">
              <span className="auth-badge">Citizen</span>
              <h1 className="auth-panel-title">Create account</h1>
              <p className="muted auth-panel-lead">
                Enter your 10-digit mobile number. We verify it with OTP before creating your account.
              </p>
            </div>
            <form className="auth-form auth-form--spacer" onSubmit={onSubmit}>
              {error ? <div className="error-banner">{error}</div> : null}
              {info ? <div className="info-banner" style={{ marginBottom: 12, padding: '10px 12px', borderRadius: 8, background: 'var(--surface-muted, #ecfdf5)', color: 'var(--text-primary)' }}>{info}</div> : null}
              <div className="field">
                <label htmlFor="r-phone">Mobile number</label>
                <PhoneInput id="r-phone" value={form.phone} onChange={(v) => set('phone', v)} />
                <p className="muted" style={{ fontSize: 13, marginTop: 6 }}>10 digits only (e.g. 9876543210)</p>
              </div>
              <div className="field">
                <button
                  type="button"
                  className="btn-secondary btn-pill"
                  onClick={sendOtp}
                  disabled={otpBusy || !isValidIndianMobile10(form.phone)}
                >
                  {otpBusy ? 'Sending…' : otpSent ? 'Resend OTP' : 'Send OTP'}
                </button>
                {devOtp ? (
                  <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>
                    Demo OTP (no SMS): <strong>{devOtp}</strong>
                  </p>
                ) : null}
              </div>
              {otpSent ? (
                <div className="field">
                  <label htmlFor="r-otp">OTP</label>
                  <input
                    id="r-otp"
                    className="input input-auth-line"
                    inputMode="numeric"
                    placeholder="6-digit code"
                    maxLength={8}
                    value={form.otp}
                    onChange={(e) => set('otp', digitsOnlyPhoneInput(e.target.value).slice(0, 8))}
                    required
                  />
                </div>
              ) : null}
              <div className="field">
                <label htmlFor="r-name">Full name</label>
                <input
                  id="r-name"
                  className="input input-auth-line"
                  placeholder="Your name"
                  value={form.full_name}
                  onChange={(e) => set('full_name', e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="r-email">Email (optional)</label>
                <input
                  id="r-email"
                  type="email"
                  className="input input-auth-line"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={(e) => set('email', e.target.value)}
                />
                <p className="muted" style={{ fontSize: 13, marginTop: 6 }}>Must include @ if provided</p>
              </div>
              <LanguageSelect
                id="r-lang"
                className="select select-auth-line"
                label="Preferred language"
                value={form.preferred_language}
                onChange={(e) => set('preferred_language', e.target.value)}
              />
              <div className="field">
                <label htmlFor="r-pass">Password</label>
                <input
                  id="r-pass"
                  type="password"
                  className="input input-auth-line"
                  placeholder="Min. 8 characters"
                  value={form.password}
                  onChange={(e) => set('password', e.target.value)}
                  minLength={8}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="r-pass2">Confirm password</label>
                <input
                  id="r-pass2"
                  type="password"
                  className="input input-auth-line"
                  placeholder="Repeat password"
                  value={form.confirm_password}
                  onChange={(e) => set('confirm_password', e.target.value)}
                  minLength={8}
                  required
                />
              </div>
              <div className="auth-pill-row">
                <button type="submit" className="btn-primary btn-pill auth-submit-primary" disabled={busy || !otpSent}>
                  {busy ? 'Creating…' : 'Register'}
                </button>
                <Link to="/login" className="btn-secondary btn-pill auth-submit-secondary">
                  Log in
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
