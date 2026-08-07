import { useState } from 'react'

const SUGGESTED = [
  'How do I track my complaint?',
  'शिकायत की स्थिति कैसे देखें?',
  'Where is my tracking ID?',
  'What do statuses like submitted and resolved mean?',
]

export default function FaqPage() {
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [matches, setMatches] = useState([])

  async function submit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    setMatches([])
    try {
      const res = await fetch('/api/v1/ai/faq/query/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error?.message || 'Request failed')
      setMatches(data.matches || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container" style={{ maxWidth: 640 }}>
      <div className="faq-hero-banner glass-card">
        <img
          src="/branding/faq-hero.png"
          alt=""
          width={1200}
          height={630}
          className="faq-hero-img"
          decoding="async"
        />
      </div>
      <div className="section-tag" style={{ marginTop: 24 }}>
        Support
      </div>
      <h1 className="page-title">Complaint status help</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        Ask about <strong>tracking your ticket</strong>, <strong>status meanings</strong>, or <strong>where to find your tracking ID</strong> — in English or Hindi. This assistant does not answer unrelated topics.
      </p>
      <form className="glass-card" onSubmit={submit}>
        {error ? <div className="error-banner">{error}</div> : null}
        <div className="field">
          <label htmlFor="faq-q">Your question</label>
          <textarea
            id="faq-q"
            className="textarea"
            rows={3}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. मेरी शिकायत का स्टेटस कैसे चेक करूँ? / How do I check my complaint status?"
          />
        </div>
        <p className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
          Try:
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {SUGGESTED.map((s) => (
            <button
              key={s}
              type="button"
              className="btn-secondary"
              style={{ padding: '8px 12px', fontSize: 13 }}
              onClick={() => setQ(s)}
            >
              {s.length > 42 ? `${s.slice(0, 40)}…` : s}
            </button>
          ))}
        </div>
        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={busy}>
          {busy ? 'Searching…' : 'Find answer'}
        </button>
      </form>
      {matches.length > 0 ? (
        <div className="glass-card" style={{ marginTop: 20 }}>
          <h3 style={{ marginBottom: 12 }}>Answers</h3>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 16 }}>
            {matches.map((m) => (
              <li key={m.id} style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 12 }}>
                <p style={{ fontWeight: 700, marginBottom: 6 }}>{m.question}</p>
                <p className="muted" style={{ lineHeight: 1.65, whiteSpace: 'pre-wrap' }}>
                  {m.answer}
                </p>
                {m.id !== 'fallback-status' ? (
                  <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                    Match score: {m.confidence}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
