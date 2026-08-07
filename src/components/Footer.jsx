import { Link } from 'react-router-dom'

const marketing = import.meta.env.VITE_MARKETING_URL || 'http://localhost:3001'

export default function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="site-footer">
      <div className="container site-footer-inner">
        <div className="site-footer-brand">
          <span className="site-footer-name">Nagrik Awaaz</span>
          <span className="site-footer-tagline">Civic intelligence platform</span>
        </div>
        <nav className="site-footer-nav" aria-label="Footer">
          <Link to="/track">Track ticket</Link>
          <Link to="/faq">FAQ</Link>
          <a href={marketing} target="_blank" rel="noreferrer">
            Marketing site
          </a>
        </nav>
        <p className="site-footer-copy">
          © {year} Nagrik Awaaz · Built for transparent public grievance redressal.
        </p>
      </div>
    </footer>
  )
}
