import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const TRUST_PILLS = [
  { label: 'End-to-end workflow', sub: 'Capture → route → resolve' },
  { label: 'Multilingual', sub: 'Vernacular-first reporting' },
  { label: 'Role-based access', sub: 'Citizen · Officer · Admin' },
  { label: 'Observable ops', sub: 'Desk, SLA hints, insights' },
]

const FEATURES = [
  {
    title: 'Voice → structured report',
    desc: 'Capture audio in the field; transcription prefills the complaint so officers receive consistent, searchable records.',
    img: '/branding/voice-feature.png',
    alt: 'Voice reporting',
  },
  {
    title: 'Desk & intelligence',
    desc: 'Triage queues, status transitions, duplicate signals, and SLA-oriented views keep teams aligned without spreadsheets.',
    img: '/branding/officer-desk.png',
    alt: 'Operations desk',
  },
  {
    title: 'Trust & transparency',
    desc: 'Public tracking, geo context, and verification-style workflows strengthen accountability between citizens and departments.',
    img: '/branding/trust-verification.png',
    alt: 'Community trust',
  },
]

export default function HomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="page-hero page-hero--premium">
      <div className="page-hero-inner container">
        <div className="grid-2 home-hero-grid">
          <div className="home-hero-copy">
            <div className="section-tag section-tag--shine">Civic operations platform</div>
            <h1 className="home-display-title">
              Turn citizen voice into{' '}
              <span className="gradient-text">actionable governance</span>
            </h1>
            <p className="home-subtitle">
              Nagrik Awaaz unifies voice capture, AI-assisted classification, geospatial context, and officer workflows in a
              single audited path — so issues move from report to resolution with clarity.
            </p>
            <ul className="home-checklist">
              <li>Speech-to-text with intelligent form handoff</li>
              <li>Duplicate awareness and category intelligence</li>
              <li>Live desk tools for field teams and administrators</li>
              <li>Public tracking and authenticated dashboards</li>
            </ul>
            <div className="home-cta-row">
              {isAuthenticated ? (
                <>
                  <Link to="/voice" className="btn-primary">
                    Start voice report
                  </Link>
                  <Link to="/complaints/new" className="btn-secondary">
                    New typed report
                  </Link>
                </>
              ) : (
                <>
                  <Link to="/register" className="btn-primary">
                    Create account
                  </Link>
                  <Link to="/login" className="btn-secondary">
                    Sign in
                  </Link>
                </>
              )}
              <Link to="/track" className="btn-soft btn-soft--emphasis">
                Track a ticket
              </Link>
              <Link to="/faq" className="btn-ghost">
                FAQ assistant
              </Link>
            </div>
          </div>
          <div className="home-hero-visual">
            <div className="home-hero-frame surface-elevated">
              <img
                src="/branding/hero-wide.png"
                alt="Citizens engaging with civic reporting tools"
                width={960}
                height={540}
                className="home-hero-img"
                decoding="async"
                loading="eager"
              />
            </div>
            <p className="home-hero-caption">Operational overview · citizen-centric reporting pipeline</p>
          </div>
        </div>

        <section className="home-trust-strip" aria-label="Platform qualities">
          {TRUST_PILLS.map((t) => (
            <div key={t.label} className="home-trust-pill">
              <span className="home-trust-label">{t.label}</span>
              <span className="home-trust-sub muted">{t.sub}</span>
            </div>
          ))}
        </section>

        <section className="home-feature-head">
          <h2 className="home-section-title">Designed for teams on the ground</h2>
          <p className="home-section-lead muted">
            Three lenses — intake, command centre, and trust — mirror how modern civic programmes actually run.
          </p>
        </section>

        <section className="home-feature-strip" aria-label="Product pillars">
          {FEATURES.map((f) => (
            <article key={f.title} className="glass-card home-feature-card surface-interactive">
              <div className="home-feature-thumb">
                <img src={f.img} alt={f.alt} width={640} height={360} loading="lazy" decoding="async" />
              </div>
              <h3 className="home-feature-title">{f.title}</h3>
              <p className="muted home-feature-desc">{f.desc}</p>
            </article>
          ))}
        </section>

        <section className="home-cta-band">
          <div className="home-cta-band-inner">
            <div>
              <h2 className="home-cta-band-title">Ready to route your next issue?</h2>
              <p className="muted home-cta-band-lead">
                Access voice intake, officer consoles, and analytics with the same credentials — role-aware by design.
              </p>
            </div>
            <div className="home-cta-band-actions">
              {isAuthenticated ? (
                <Link to="/complaints/new" className="btn-primary">
                  File a report
                </Link>
              ) : (
                <Link to="/register" className="btn-primary">
                  Get started
                </Link>
              )}
              <Link to="/track" className="btn-secondary">
                Track existing ticket
              </Link>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
