import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'
import Agent1Panel from '../components/Agent1Panel'
import LanguageSelect from '../components/LanguageSelect'
import { geoErrorMessage, requestDeviceLocation } from '../utils/geoLocation'

/** Backend stores lat/lng as Decimal(9,6); GPS floats need rounding before JSON. */
function roundCoord(value, decimals = 6) {
  if (value == null || !Number.isFinite(Number(value))) return null
  return parseFloat(Number(value).toFixed(decimals))
}

const VOICE_DRAFT_KEY = 'awaaz_voice_new_complaint'

function formatActionError(e) {
  if (e && typeof e === 'object' && 'message' in e) {
    if (e.status === 401) {
      return 'Session expired or not signed in. Log out and log in again, then retry.'
    }
    return String(e.message || 'Request failed')
  }
  return 'Request failed'
}

export default function NewComplaintPage() {
  const { access, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const [categories, setCategories] = useState([])
  const [categoriesLoadFailed, setCategoriesLoadFailed] = useState(false)
  const [dupes, setDupes] = useState([])
  const [hints, setHints] = useState([])
  const [form, setForm] = useState({
    title: '',
    description: '',
    description_language: 'hi',
    category_id: '',
    city: '',
    ward: '',
    address: '',
    pincode: '',
    source: 'web',
    is_anonymous: false,
    latitude: null,
    longitude: null,
  })
  const [aiHint, setAiHint] = useState(null)
  const [extracted, setExtracted] = useState([])
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)
  const [tools, setTools] = useState({
    ai: false,
    dupes: false,
    hints: false,
    gps: false,
    extract: false,
  })
  const [agentBusy, setAgentBusy] = useState(false)

  /**
   * Prefill from voice flow: React Router state (avoids huge / fragile query strings),
   * then ?transcript= legacy query, then sessionStorage after refresh.
   */
  useEffect(() => {
    let transcript = ''
    let langHint = ''
    let voiceStub = false
    let transcriptionFailed = false

    const st = location.state
    if (st && typeof st === 'object' && st.transcript != null && String(st.transcript).length > 0) {
      transcript = String(st.transcript)
      langHint = typeof st.lang === 'string' ? st.lang : ''
      voiceStub = !!st.voiceStub
      transcriptionFailed = !!st.transcriptionFailed
    }

    if (!transcript) {
      const tr = searchParams.get('transcript')
      if (tr) {
        transcript = tr
        langHint = searchParams.get('lang') || ''
      }
    }

    if (!transcript) {
      try {
        const raw = sessionStorage.getItem(VOICE_DRAFT_KEY)
        if (raw) {
          const o = JSON.parse(raw)
          if (o.transcript != null && String(o.transcript).length > 0) {
            transcript = String(o.transcript)
            langHint = typeof o.lang === 'string' ? o.lang : ''
            voiceStub = !!o.voiceStub
            transcriptionFailed = !!o.transcriptionFailed
          }
          sessionStorage.removeItem(VOICE_DRAFT_KEY)
        }
      } catch {
        /* ignore */
      }
    }

    if (!transcript || transcriptionFailed) return
    if (String(transcript).trim().startsWith('[')) return

    queueMicrotask(() => {
      setForm((f) => ({
        ...f,
        description: transcript,
        description_language: langHint && langHint.length <= 5 ? langHint : f.description_language,
      }))
      if (voiceStub) {
        setInfo(
          'Demo speech-to-text: Whisper is not installed on the backend, so the description is a placeholder. Edit it or install openai-whisper on the server for real transcripts.',
        )
      } else {
        setInfo('Voice transcript loaded — fill city/address if needed, then run Agent1 below.')
      }
    })
  }, [location.key, location.state, searchParams])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const list = await api('/complaints/categories/')
        if (!cancelled) {
          setCategories(Array.isArray(list) ? list : [])
          setCategoriesLoadFailed(false)
        }
      } catch {
        if (!cancelled) {
          setCategories([])
          setCategoriesLoadFailed(true)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  function setToolBusy(key, v) {
    setTools((t) => ({ ...t, [key]: v }))
  }

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }))
  }

  async function suggestCategory() {
    setAiHint(null)
    setInfo('')
    if (!access) {
      setError('You must be logged in to use AI tools.')
      return
    }
    if (!form.description.trim() || form.description.length < 5) {
      setError('Enter at least 5 characters for AI suggest.')
      return
    }
    setError('')
    setToolBusy('ai', true)
    try {
      const r = await api('/ai/classify/', {
        method: 'POST',
        token: access,
        body: { text: form.description, language: form.description_language },
      })
      setAiHint(r)
      const match = categories.find((category) => category.name === r.category)
      if (match) setForm((f) => ({ ...f, category_id: String(match.id) }))
      const languageNote = r.translation_status === 'unavailable'
        ? ' Translation is not configured, so non-English text may be classified less accurately.'
        : ''
      setInfo(`Suggested category: ${r.category}. Review it below or choose another category.${languageNote}`)
    } catch (e) {
      setError(formatActionError(e))
    } finally {
      setToolBusy('ai', false)
    }
  }

  async function checkDuplicates() {
    setDupes([])
    setInfo('')
    if (!access) {
      setError('You must be logged in to check duplicates.')
      return
    }
    if (!form.description.trim() || form.description.length < 10) {
      setError('Enter at least 10 characters to check duplicates.')
      return
    }
    setError('')
    setToolBusy('dupes', true)
    try {
      const r = await api('/complaints/check-duplicates/', {
        method: 'POST',
        token: access,
        body: {
          description: form.description,
          city: form.city,
          ward: form.ward,
        },
      })
      const list = r.possible_duplicates || []
      setDupes(list)
      setInfo(
        list.length === 0
          ? 'No similar open complaints found (or nothing close enough to match).'
          : `Found ${list.length} possible similar complaint(s).`,
      )
    } catch (e) {
      setError(formatActionError(e))
    } finally {
      setToolBusy('dupes', false)
    }
  }

  async function extractLocationHints() {
    setExtracted([])
    setInfo('')
    if (!access) {
      setError('You must be logged in to extract location hints.')
      return
    }
    if (!form.description.trim()) {
      setError('Enter description text first.')
      return
    }
    setError('')
    setToolBusy('extract', true)
    try {
      const r = await api('/ai/extract-location/', {
        method: 'POST',
        token: access,
        body: { text: form.description },
      })
      const items = r.extracted || []
      setExtracted(items)
      setInfo(
        items.length === 0
          ? 'No location phrases detected in the text (try adding area, landmark, or PIN).'
          : 'Location hints detected below.',
      )
      const pin = items.find((x) => String(x).startsWith('PIN '))
      if (pin) {
        const code = pin.replace(/^PIN\s+/, '')
        if (/^\d{6}$/.test(code)) setForm((f) => ({ ...f, pincode: code }))
      }
    } catch (e) {
      setError(formatActionError(e))
    } finally {
      setToolBusy('extract', false)
    }
  }

  async function loadHints() {
    setHints([])
    setInfo('')
    setError('')
    setToolBusy('hints', true)
    try {
      const q = new URLSearchParams()
      if (form.category_id) q.set('category_id', String(form.category_id))
      if (form.city.trim()) q.set('city', form.city.trim())
      const r = await api(`/complaints/hints/?${q}`)
      const rows = r.suggestions || []
      setHints(rows)
      setInfo(
        rows.length === 0
          ? 'No demo “past resolution” examples for these filters. Try another category or add a city.'
          : `Showing ${rows.length} demo resolution hint(s).`,
      )
    } catch (e) {
      setError(formatActionError(e))
    } finally {
      setToolBusy('hints', false)
    }
  }

  async function applyCoordinates(lat, lng, message) {
    setForm((f) => ({ ...f, latitude: lat, longitude: lng }))
    try {
      const rev = await api(`/complaints/geo/reverse/?lat=${lat}&lng=${lng}`)
      setForm((f) => ({ ...f, address: rev.display_name || f.address }))
      setInfo(message)
    } catch {
      setInfo(`${message} Address lookup failed — you can edit address manually.`)
    }
  }

  async function useApproximateLocation() {
    setInfo('')
    setError('')
    setToolBusy('gps', true)
    try {
      const approx = await api('/complaints/geo/ip/')
      const lat = roundCoord(approx.latitude)
      const lng = roundCoord(approx.longitude)
      await applyCoordinates(
        lat,
        lng,
        `Approximate location saved (${lat}, ${lng}) — ${approx.display_name || 'network estimate'}.`,
      )
    } catch (e) {
      setError(formatActionError(e) || 'Approximate location lookup failed.')
    } finally {
      setToolBusy('gps', false)
    }
  }

  async function useMyLocation() {
    setInfo('')
    setError('')
    if (!navigator.geolocation) {
      await useApproximateLocation()
      return
    }
    if (!window.isSecureContext) {
      setError('GPS needs http://localhost:5173. Trying approximate location instead…')
      await useApproximateLocation()
      return
    }
    setToolBusy('gps', true)
    try {
      const pos = await requestDeviceLocation()
      const lat = roundCoord(pos.coords.latitude)
      const lng = roundCoord(pos.coords.longitude)
      await applyCoordinates(lat, lng, `GPS captured (${lat}, ${lng}).`)
    } catch (gpsErr) {
      try {
        const approx = await api('/complaints/geo/ip/')
        const lat = roundCoord(approx.latitude)
        const lng = roundCoord(approx.longitude)
        await applyCoordinates(
          lat,
          lng,
          `Device GPS unavailable — saved approximate location (${lat}, ${lng}): ${approx.display_name || 'network estimate'}.`,
        )
      } catch {
        setError(geoErrorMessage(gpsErr))
      }
    } finally {
      setToolBusy('gps', false)
    }
  }

  function handleAgentProcessed(data) {
    if (!data) return
    if (data.english_text && data.english_text.length > 10) {
      setForm((f) => ({ ...f, description: data.english_text }))
    }
    const catName = data.nagrik_category
    if (catName && categories.length) {
      const match = categories.find((c) => c.name === catName)
      if (match) setForm((f) => ({ ...f, category_id: String(match.id) }))
    }
    setAiHint({
      category: data.nagrik_category || data.department,
      confidence: data.classification?.confidence ?? 0,
      urgency_score: data.classification?.urgency_score ?? 0.35,
      suggested_priority: data.priority?.toLowerCase(),
      department: data.department,
      subcategory: data.subcategory,
      classification_source: data.classification?.classification_source || 'agent1',
      sentiment_polarity: data.classification?.sentiment_polarity,
      agent1: true,
    })
  }

  const userMobile = user?.phone ? String(user.phone).replace(/\D/g, '').slice(-10) : ''

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setInfo('')
    setBusy(true)
    try {
      const body = {
        title: form.title.trim(),
        description: form.description.trim(),
        description_language: form.description_language,
        city: form.city.trim(),
        ward: form.ward.trim(),
        address: form.address.trim(),
        pincode: form.pincode.trim(),
        source: form.source,
        is_anonymous: form.is_anonymous,
      }
      if (form.latitude != null && form.longitude != null) {
        body.latitude = roundCoord(form.latitude)
        body.longitude = roundCoord(form.longitude)
      }
      const cid = form.category_id
      if (cid !== '' && cid != null) {
        const n = Number(cid)
        if (!Number.isNaN(n)) body.category_id = n
      }
      const res = await api('/complaints/', { method: 'POST', token: access, body })
      navigate(`/complaints/${res.complaint.id}`)
    } catch (e) {
      setError(formatActionError(e))
    } finally {
      setBusy(false)
    }
  }

  const anyToolRunning = Object.values(tools).some(Boolean)
  const toolDisabled = busy || agentBusy || anyToolRunning

  return (
    <div className="container" style={{ maxWidth: 640 }}>
      <Link to="/complaints" className="muted" style={{ display: 'inline-block', marginBottom: 16 }}>
        ← My complaints
      </Link>
      <div className="section-tag">Report</div>
      <h1 className="page-title">New complaint</h1>
      <p className="muted" style={{ marginBottom: 24 }}>
        Geo-tag with GPS, check duplicates, and view past resolutions — aligned with the project approval & deployment
        roadmap.
      </p>
      <form className="glass-card complaint-form-card" onSubmit={onSubmit}>
        {error ? <div className="error-banner">{error}</div> : null}
        {info ? (
          <div className="info-banner" style={{ marginBottom: 16 }}>
            {info}
          </div>
        ) : null}
        {categoriesLoadFailed ? (
          <p className="muted" style={{ marginBottom: 12, fontSize: 14 }}>
            Could not load categories from the API. You can still submit; category can stay “Auto / AI” or try refreshing the
            page.
          </p>
        ) : null}
        <div className="field">
          <label htmlFor="t">Title (optional)</label>
          <input id="t" className="input" value={form.title} onChange={(e) => set('title', e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="d">Description *</label>
          <textarea
            id="d"
            className="textarea"
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            placeholder="Type in Hindi, English, Tamil, or Marathi…"
            required
          />
          <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>
            Supported languages: Hindi, English, Tamil, Marathi. Pick below, or use{' '}
            <Link to="/voice">Voice report</Link> to speak.
          </p>
        </div>

        <LanguageSelect
          id="lang"
          label="Complaint language"
          value={form.description_language}
          onChange={(e) => set('description_language', e.target.value)}
        />
        <div className="field">
          <label htmlFor="cat">Category (optional)</label>
          <select id="cat" className="select" value={form.category_id} onChange={(e) => set('category_id', e.target.value)}>
            <option value="">— Auto / AI —</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>
        <div className="complaint-tool-actions">
          <p className="muted" style={{ margin: '0 0 10px', fontSize: 13 }}>
            Tools below call the live API. Ensure the Django backend is running; with <code style={{ fontSize: 12 }}>npm run dev</code>{' '}
            requests are proxied to port 8000.
          </p>
          <div className="complaint-tool-buttons">
            <button
              type="button"
              className="btn-secondary"
              onClick={suggestCategory}
              disabled={toolDisabled}
              aria-busy={tools.ai}
            >
              {tools.ai ? 'AI…' : 'AI: category + urgency'}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={checkDuplicates}
              disabled={toolDisabled}
              aria-busy={tools.dupes}
            >
              {tools.dupes ? 'Checking…' : 'Check duplicates'}
            </button>
            <button type="button" className="btn-secondary" onClick={loadHints} disabled={toolDisabled} aria-busy={tools.hints}>
              {tools.hints ? 'Loading…' : 'Past resolutions'}
            </button>
            <button type="button" className="btn-secondary" onClick={useMyLocation} disabled={toolDisabled} aria-busy={tools.gps}>
              {tools.gps ? 'Locating…' : 'Use my location (GPS)'}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={useApproximateLocation}
              disabled={toolDisabled}
              aria-busy={tools.gps}
            >
              Approximate location
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={extractLocationHints}
              disabled={toolDisabled}
              aria-busy={tools.extract}
            >
              {tools.extract ? 'Extracting…' : 'Extract location (speech NLP)'}
            </button>
          </div>
        </div>
        {extracted.length > 0 ? (
          <p className="muted" style={{ marginBottom: 14 }}>
            <strong>Detected from text:</strong> {extracted.join(' · ')}
          </p>
        ) : null}
        {aiHint ? (
          <p className="muted" style={{ marginBottom: 14 }}>
            AI: <strong style={{ color: 'var(--text-primary)' }}>{aiHint.category}</strong>
            {aiHint.department ? ` · ${aiHint.department}` : ''}
            {aiHint.subcategory ? ` / ${aiHint.subcategory}` : ''}
            {` · ${aiHint.classification_source || 'classifier'} · score ${(Number(aiHint.confidence) * 100).toFixed(0)}%`}{' '}
            {aiHint.urgency_score != null ? (
              <>
                · Priority: <strong>{aiHint.suggested_priority || 'normal'}</strong>
                {' '}· Urgency: <strong>{Number(aiHint.urgency_score).toFixed(2)}</strong>
              </>
            ) : null}
            {aiHint.sentiment_polarity != null ? ` · TextBlob polarity: ${Number(aiHint.sentiment_polarity).toFixed(2)}` : ''}
          </p>
        ) : null}
        {dupes.length > 0 ? (
          <div className="glass-card" style={{ marginBottom: 16, padding: 16 }}>
            <strong>Possible duplicates</strong>
            <ul style={{ marginTop: 8, paddingLeft: 18 }}>
              {dupes.map((d) => (
                <li key={d.id} className="muted" style={{ fontSize: 14 }}>
                  {d.tracking_id} — {d.title || 'No title'} ({d.status})
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {hints.length > 0 ? (
          <div className="glass-card" style={{ marginBottom: 16, padding: 16 }}>
            <strong>Similar resolved cases (demo)</strong>
            <ul style={{ marginTop: 8, paddingLeft: 18 }}>
              {hints.map((h, i) => (
                <li key={i} className="muted" style={{ fontSize: 14 }}>
                  {h.tracking_id} — {h.title || h.category} ({h.note})
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="grid-2">
          <div className="field">
            <label htmlFor="city">City</label>
            <input id="city" className="input" value={form.city} onChange={(e) => set('city', e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="ward">Ward</label>
            <input id="ward" className="input" value={form.ward} onChange={(e) => set('ward', e.target.value)} />
          </div>
        </div>
        <div className="field">
          <label htmlFor="addr">Address</label>
          <textarea id="addr" className="textarea" style={{ minHeight: 72 }} value={form.address} onChange={(e) => set('address', e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="pin">Pincode</label>
          <input id="pin" className="input" value={form.pincode} onChange={(e) => set('pincode', e.target.value)} />
        </div>

        <Agent1Panel
          access={access}
          text={form.description}
          userLanguage={form.description_language}
          complainantName={user?.full_name || ''}
          mobile={userMobile}
          email={user?.email || ''}
          title={form.title}
          city={form.city}
          ward={form.ward}
          address={form.address}
          pincode={form.pincode}
          onProcessed={handleAgentProcessed}
          onBusyChange={setAgentBusy}
        />

        <label className="check">
          <input type="checkbox" checked={form.is_anonymous} onChange={(e) => set('is_anonymous', e.target.checked)} />
          Submit anonymously (your account will not be linked on the server)
        </label>
        <button type="submit" className="btn-primary" style={{ width: '100%', marginTop: 20 }} disabled={busy || agentBusy}>
          {busy ? 'Submitting…' : 'Submit complaint'}
        </button>
      </form>
    </div>
  )
}
