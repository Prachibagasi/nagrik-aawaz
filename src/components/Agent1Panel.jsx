import { useCallback, useState } from 'react'
import { api } from '../api/client'

const PREFILL_KEY = 'nagrik_dept_prefill'

function formatErr(e) {
  if (e && typeof e === 'object' && 'message' in e) return String(e.message)
  return 'Agent processing failed'
}

function encodePrefillPayload(data) {
  return btoa(unescape(encodeURIComponent(JSON.stringify(data))))
}

function buildPortalUrl(baseUrl, prefillData) {
  const url = new URL(baseUrl)
  url.searchParams.set('nagrik_prefill', encodePrefillPayload(prefillData))
  return url.toString()
}

/** Agent1 — run after citizen fills complaint + location; routes to department dummy portal. */
export default function Agent1Panel({
  access,
  text,
  userLanguage = 'hi',
  complainantName = '',
  mobile = '',
  email = '',
  title = '',
  city = '',
  ward = '',
  address = '',
  pincode = '',
  onProcessed,
  onBusyChange,
}) {
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [showDraft, setShowDraft] = useState(false)
  const [deptSubmitted, setDeptSubmitted] = useState(null)

  const setBusyState = (v) => {
    setBusy(v)
    onBusyChange?.(v)
  }

  const locationLine = [address, ward, city, pincode].filter(Boolean).join(', ')

  const runAgent = useCallback(async () => {
    const trimmed = (text || '').trim()
    if (!access) {
      setError('Log in to run the AI agent.')
      return
    }
    if (trimmed.length < 3) {
      setError('Enter a complaint description first (at least a few words).')
      return
    }
    setError('')
    setBusyState(true)
    setDeptSubmitted(null)
    try {
      const data = await api('/ai/process-complaint/', {
        method: 'POST',
        token: access,
        body: {
          text: trimmed,
          user_language: userLanguage,
          complainant_name: complainantName,
          mobile: mobile.replace(/\D/g, '').slice(-10),
          email: email.trim(),
          title: title.trim(),
          city: city.trim(),
          district: city.trim(),
          ward: ward.trim(),
          address: address.trim(),
          pincode: pincode.trim(),
          location: locationLine,
        },
      })
      setResult(data)
      setShowDraft(false)
      onProcessed?.(data)
    } catch (e) {
      setError(formatErr(e))
    } finally {
      setBusyState(false)
    }
  }, [
    access,
    text,
    userLanguage,
    complainantName,
    mobile,
    email,
    title,
    city,
    ward,
    address,
    pincode,
    locationLine,
    onProcessed,
  ])

  async function submitToDepartmentApi() {
    if (!result?.portal) return
    setBusyState(true)
    setError('')
    try {
      const created = await api(result.portal.api_path, {
        method: 'POST',
        body: { ...result.portal.form_payload },
      })
      setDeptSubmitted(created)
    } catch (e) {
      setError(formatErr(e))
    } finally {
      setBusyState(false)
    }
  }

  function openDepartmentPortal() {
    if (!result?.portal) return
    const prefillData = {
      complaint_id: result.complaint_id,
      portal_key: result.portal.key,
      form_payload: result.portal.form_payload,
    }
    try {
      sessionStorage.setItem(PREFILL_KEY, JSON.stringify(prefillData))
    } catch {
      /* ignore */
    }
    window.open(buildPortalUrl(result.portal.portal_url, prefillData), '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="agent1-panel glass-card" style={{ marginTop: 8, marginBottom: 8, padding: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div className="section-tag" style={{ marginBottom: 6 }}>
            Agent1 — department routing
          </div>
          <h3 style={{ margin: 0, fontSize: 18 }}>Send to government department portal</h3>
          <p className="muted" style={{ fontSize: 13, marginTop: 6, marginBottom: 0 }}>
            Fill description and location above, then run the agent. It uses <strong>all your details</strong> (name, phone,
            email, address) to classify the department and pre-fill the matching demo site (Bijli / Jal / PWD / Shiksha).
          </p>
        </div>
        <button type="button" className="btn-primary" onClick={runAgent} disabled={busy} style={{ flexShrink: 0 }}>
          {busy ? 'Processing…' : result ? 'Re-run agent' : 'Run AI agent'}
        </button>
      </div>

      {error ? <div className="error-banner" style={{ marginTop: 14 }}>{error}</div> : null}

      {result ? (
        <div style={{ marginTop: 16 }}>
          <div className="agent1-dept-badge">
            <span className="agent1-dept-label">Assigned department</span>
            <strong>{result.department}</strong>
            <span className="muted" style={{ fontSize: 13 }}>
              · {result.portal?.name}
            </span>
          </div>

          <div className="agent1-meta-grid">
            <div>
              <span className="muted">Complaint ID</span>
              <strong>{result.complaint_id}</strong>
            </div>
            <div>
              <span className="muted">Issue type</span>
              <strong>{result.subcategory}</strong>
            </div>
            <div>
              <span className="muted">Priority</span>
              <strong>{result.priority}</strong>
            </div>
            <div>
              <span className="muted">Authority</span>
              <strong style={{ fontSize: 13 }}>{result.authority}</strong>
            </div>
          </div>

          {result.portal?.form_payload ? (
            <p className="muted" style={{ fontSize: 13, marginTop: 12 }}>
              <strong>Portal pre-fill:</strong> {result.portal.form_payload.name}
              {result.portal.form_payload.mobile ? ` · ${result.portal.form_payload.mobile}` : ''}
              {result.portal.form_payload.email ? ` · ${result.portal.form_payload.email}` : ''}
              {result.portal.form_payload.location || result.portal.form_payload.district
                ? ` · ${result.portal.form_payload.location || result.portal.form_payload.district}`
                : ''}
            </p>
          ) : null}

          <div style={{ marginTop: 12 }}>
            <button type="button" className="btn-ghost" onClick={() => setShowDraft((v) => !v)} style={{ padding: '6px 0' }}>
              {showDraft ? 'Hide formal draft letter ▲' : 'Show formal draft letter ▼'}
            </button>
            {showDraft ? <pre className="agent1-draft">{result.draft_letter}</pre> : null}
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 16 }}>
            <button type="button" className="btn-secondary" onClick={openDepartmentPortal} disabled={busy}>
              Open department portal (pre-filled)
            </button>
            <button type="button" className="btn-secondary" onClick={submitToDepartmentApi} disabled={busy}>
              Submit to department API
            </button>
          </div>

          {deptSubmitted ? (
            <div className="info-banner" style={{ marginTop: 14 }}>
              Registered on department portal as <strong>{deptSubmitted.id}</strong>
              {deptSubmitted.nagrik_complaint_id ? <> · linked to {deptSubmitted.nagrik_complaint_id}</> : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export { PREFILL_KEY }
