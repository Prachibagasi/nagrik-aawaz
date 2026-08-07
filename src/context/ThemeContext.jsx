import { createContext, useContext, useEffect, useMemo } from 'react'

const ThemeContext = createContext(null)
const STORAGE_KEY = 'nagrik-theme'

/**
 * App uses the same light theme as nagrik-awaaz-website (nagrik-awaaz.html) only.
 */
export function ThemeProvider({ children }) {
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'light')
    document.documentElement.classList.remove('dark')
    document.documentElement.classList.add('light')
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      /* ignore */
    }
  }, [])

  const value = useMemo(
    () => ({
      isDark: false,
      /** no-op: kept so any stray useTheme callers do not break */
      toggleTheme: () => {},
    }),
    [],
  )

  return (
    <ThemeContext.Provider value={value}>
      <div className="app-shell light">{children}</div>
    </ThemeContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components -- context hook
export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
