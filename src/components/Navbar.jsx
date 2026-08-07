import { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const marketing = import.meta.env.VITE_MARKETING_URL || 'http://localhost:3001'

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [menuOpen])

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 881px)')
    const closeIfWide = () => {
      if (mq.matches) setMenuOpen(false)
    }
    mq.addEventListener('change', closeIfWide)
    return () => mq.removeEventListener('change', closeIfWide)
  }, [])

  const closeMenu = () => setMenuOpen(false)

  return (
    <header className="site-header">
      {menuOpen ? (
        <button type="button" className="nav-backdrop" aria-label="Close menu" onClick={closeMenu} />
      ) : null}
      <div className="container site-header-inner">
        <Link to="/" className="navbar-logo" aria-label="Nagrik Awaaz home" onClick={closeMenu}>
          <img
            src="/branding/nagrik-awaaz-logo.png"
            alt="Nagrik Awaaz"
            className="navbar-logo-img"
            width={220}
            height={52}
            decoding="async"
          />
        </Link>

        <button
          type="button"
          className={`nav-toggle ${menuOpen ? 'nav-toggle--open' : ''}`}
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          onClick={() => setMenuOpen((o) => !o)}
        >
          <span className="nav-toggle-bar" />
          <span className="nav-toggle-bar" />
          <span className="nav-toggle-bar" />
        </button>

        <nav
          id="primary-navigation"
          className={`nav-cluster ${menuOpen ? 'nav-cluster--open' : ''}`}
          onClick={(e) => {
            if (e.target.closest('a, button')) closeMenu()
          }}
        >
          <a href={marketing} target="_blank" rel="noreferrer" className="btn-ghost nav-aux">
            Website
          </a>
          <NavLink to="/faq" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
            FAQ
          </NavLink>
          {isAuthenticated ? (
            <>
              <NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
                Dashboard
              </NavLink>
              <NavLink to="/complaints" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
                My complaints
              </NavLink>
              <NavLink to="/voice" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
                Voice
              </NavLink>
              <NavLink to="/complaints/new" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
                Report
              </NavLink>
              {(user?.role === 'officer' || user?.role === 'admin') && (
                <>
                  <NavLink to="/desk" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
                    Desk
                  </NavLink>
                  <NavLink
                    to="/insights/sentiment"
                    className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
                  >
                    Insights
                  </NavLink>
                </>
              )}
              <NavLink to="/track" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
                Track
              </NavLink>
              <NavLink to="/profile" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
                Profile
              </NavLink>
              <span className="nav-user-chip muted">
                {user?.full_name || user?.phone}
              </span>
              <button type="button" className="btn-soft" onClick={() => logout()}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
                Log in
              </NavLink>
              <Link to="/register" className="btn-primary btn-primary--compact">
                Register
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
