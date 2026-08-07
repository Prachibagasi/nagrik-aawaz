/** Base path or full origin for JSON API. Default `/api/v1` uses Vite dev proxy → Django. */
function getApiRoot() {
  const raw = import.meta.env.VITE_API_BASE_URL
  if (raw != null && String(raw).trim() !== '') {
    return String(raw).replace(/\/$/, '')
  }
  return '/api/v1'
}

const API_PREFIX = getApiRoot()

/** Strip duplicate /api/v1 when backend returns a full path segment. */
export function normalizeApiPath(path) {
  let p = path.startsWith('/') ? path : `/${path}`
  if (p.startsWith('/api/v1/')) p = p.slice('/api/v1'.length)
  if (p.startsWith('/api/v1')) p = p.slice('/api/v1'.length)
  return p || '/'
}

function fieldErrors(obj) {
  const parts = Object.entries(obj).map(([k, v]) => {
    const val = Array.isArray(v) ? v[0] : v
    if (typeof val === 'string') return val
    if (typeof val === 'object' && val !== null) return `${k}: ${JSON.stringify(val)}`
    return `${k}: ${String(val)}`
  })
  return parts.join(' · ')
}

function getMessage(payload) {
  if (!payload) return 'Request failed'
  if (payload.error?.message) return String(payload.error.message)
  if (typeof payload.detail === 'string') return payload.detail
  if (Array.isArray(payload.detail)) return payload.detail.map((x) => String(x)).join(' ')
  if (typeof payload.detail === 'object' && payload.detail !== null && !Array.isArray(payload.detail)) {
    return fieldErrors(payload.detail)
  }
  if (typeof payload.message === 'string') return payload.message
  // DRF validation errors at top level: { phone: [...], otp: [...] }
  if (typeof payload === 'object' && payload !== null && !Array.isArray(payload)) {
    const skip = new Set(['error', 'detail', 'message', 'raw'])
    const entries = Object.entries(payload).filter(([k]) => !skip.has(k))
    if (entries.length) return fieldErrors(Object.fromEntries(entries))
  }
  return 'Request failed'
}

export async function api(path, { method = 'GET', body, headers = {}, token, raw } = {}) {
  const url = `${API_PREFIX}${normalizeApiPath(path)}`
  const h = new Headers(headers)
  if (token) h.set('Authorization', `Bearer ${token}`)
  if (body !== undefined && body !== null && !raw) {
    h.set('Content-Type', 'application/json')
  }
  const opts = { method, headers: h }
  if (body !== undefined && body !== null) {
    opts.body = raw ? body : JSON.stringify(body)
  }

  let res
  try {
    res = await fetch(url, opts)
  } catch (e) {
    const name = e && typeof e === 'object' && 'name' in e ? e.name : ''
    const msg = e instanceof Error ? e.message : String(e)
    if (name === 'TypeError' || /Failed to fetch|NetworkError|Load failed|fetch/i.test(msg)) {
      throw new Error(
        'Cannot reach the API. Start the Django backend (port 8000), use `npm run dev` so requests proxy to it, or set VITE_API_BASE_URL in .env.local (e.g. http://127.0.0.1:8000/api/v1).',
      )
    }
    throw e
  }

  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { raw: text }
    }
  }
  if (!res.ok) {
    const err = new Error(getMessage(data))
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

export async function apiMultipart(path, formData, token) {
  const url = `${API_PREFIX}${normalizeApiPath(path)}`
  const h = new Headers()
  if (token) h.set('Authorization', `Bearer ${token}`)

  let res
  try {
    res = await fetch(url, { method: 'POST', headers: h, body: formData })
  } catch (e) {
    const name = e && typeof e === 'object' && 'name' in e ? e.name : ''
    const msg = e instanceof Error ? e.message : String(e)
    if (name === 'TypeError' || /Failed to fetch|NetworkError|Load failed|fetch/i.test(msg)) {
      throw new Error(
        'Cannot reach the API. Start the Django backend or set VITE_API_BASE_URL in .env.local.',
      )
    }
    throw e
  }

  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { raw: text }
    }
  }
  if (!res.ok) {
    const err = new Error(getMessage(data))
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}
