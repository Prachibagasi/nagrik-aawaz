import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

const ACCESS = 'awaaz_access'
const REFRESH = 'awaaz_refresh'

export function AuthProvider({ children }) {
  const [access, setAccess] = useState(() => localStorage.getItem(ACCESS) || '')
  const [refresh, setRefresh] = useState(() => localStorage.getItem(REFRESH) || '')
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!localStorage.getItem(ACCESS))

  const clearTokens = useCallback(() => {
    localStorage.removeItem(ACCESS)
    localStorage.removeItem(REFRESH)
    setAccess('')
    setRefresh('')
    setUser(null)
  }, [])

  const loadMe = useCallback(async (tok) => {
    const t = tok || access
    if (!t) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await api('/auth/me/', { token: t })
      setUser(me)
    } catch (err) {
      const status = err && typeof err === 'object' && 'status' in err ? err.status : 0
      // Only drop tokens when the access token is rejected. Network / 5xx on /me/ must not
      // wipe a valid JWT (that caused "logout then login does nothing" when /me/ flaked).
      if (status === 401 || status === 403) {
        clearTokens()
      } else {
        setUser(null)
      }
    } finally {
      setLoading(false)
    }
  }, [access, clearTokens])

  useEffect(() => {
    if (access) {
      queueMicrotask(() => {
        setLoading(true)
        void loadMe(access)
      })
    } else {
      queueMicrotask(() => {
        setUser(null)
        setLoading(false)
      })
    }
  }, [access, loadMe])

  const login = useCallback(async (phone, password) => {
    const data = await api('/auth/login/', { method: 'POST', body: { phone, password } })
    localStorage.setItem(ACCESS, data.access)
    localStorage.setItem(REFRESH, data.refresh)
    setAccess(data.access)
    setRefresh(data.refresh)
    await loadMe(data.access)
    return data
  }, [loadMe])

  const register = useCallback(async (payload) => {
    const data = await api('/auth/register/', { method: 'POST', body: payload })
    localStorage.setItem(ACCESS, data.tokens.access)
    localStorage.setItem(REFRESH, data.tokens.refresh)
    setAccess(data.tokens.access)
    setRefresh(data.tokens.refresh)
    await loadMe(data.tokens.access)
    return data
  }, [loadMe])

  const logout = useCallback(async () => {
    const r = refresh || localStorage.getItem(REFRESH)
    const a = access || localStorage.getItem(ACCESS)
    try {
      if (r && a) {
        await api('/auth/logout/', { method: 'POST', body: { refresh: r }, token: a })
      }
    } catch {
      /* ignore */
    }
    clearTokens()
  }, [access, refresh, clearTokens])

  const setTokens = useCallback((a, r) => {
    if (a) localStorage.setItem(ACCESS, a)
    if (r) localStorage.setItem(REFRESH, r)
    setAccess(a || '')
    setRefresh(r || '')
  }, [])

  const value = useMemo(
    () => ({
      access,
      refresh,
      user,
      loading,
      isAuthenticated: !!access,
      login,
      register,
      logout,
      setTokens,
      refreshUser: () => loadMe(),
    }),
    [access, refresh, user, loading, login, register, logout, setTokens, loadMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components -- context hook
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
