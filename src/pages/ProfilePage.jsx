import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'
import LanguageSelect from '../components/LanguageSelect'
import { validateEmailFormat } from '../utils/phone'

export default function ProfilePage() {
  const { access, refreshUser } = useAuth()
  const [form, setForm] = useState({ full_name: '', email: '', preferred_language: 'hi' })
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const me = await api('/auth/me/', { token: access })
        if (!cancelled) {
          setForm({
            full_name: me.full_name || '',
            email: me.email || '',
            preferred_language: me.preferred_language || 'hi',
          })
        }
      } catch {
        /* handled by auth */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [access])

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }))
  }

  async function onSubmit(e) {
    e.preventDefault()
    setMsg('')
    setError('')
    setBusy(true)
    try {
      const body = {
        full_name: form.full_name.trim(),
        preferred_language: form.preferred_language,
      }
      if (form.email.trim()) body.email = validateEmailFormat(form.email)
      await api('/auth/me/', { method: 'PATCH', token: access, body })
      await refreshUser()
      setMsg('Profile updated.')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container" style={{ maxWidth: 480 }}>
      <div className="section-tag">Account</div>
      <h1 className="page-title">Profile</h1>
      <form className="glass-card" onSubmit={onSubmit}>
        {error ? <div className="error-banner">{error}</div> : null}
        {msg ? <div className="success-banner">{msg}</div> : null}
        <div className="field">
          <label htmlFor="fn">Full name</label>
          <input id="fn" className="input" value={form.full_name} onChange={(e) => set('full_name', e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="em">Email</label>
          <input id="em" type="email" className="input" placeholder="you@example.com" value={form.email} onChange={(e) => set('email', e.target.value)} />
          <p className="muted" style={{ fontSize: 13, marginTop: 6 }}>Must include @ if provided</p>
        </div>
        <LanguageSelect
          id="pl"
          label="Preferred language"
          value={form.preferred_language}
          onChange={(e) => set('preferred_language', e.target.value)}
        />
        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={busy}>
          {busy ? 'Saving…' : 'Save changes'}
        </button>
      </form>
    </div>
  )
}
