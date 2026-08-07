/** Robust browser geolocation — multiple strategies for Windows / Chrome quirks. */

export class GeoLocationError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'GeoLocationError'
    this.code = code
  }
}

export function geoErrorMessage(err) {
  if (err instanceof GeoLocationError) return err.message
  if (!err) return 'Could not read location. Check browser permission and retry.'
  switch (err.code) {
    case 1:
      return (
        'Location permission blocked. Click the lock icon in the address bar → Site settings → ' +
        'Location → Allow, then retry.'
      )
    case 2:
      return (
        'Device GPS unavailable. In Windows Settings → Privacy → Location, also turn ON ' +
        '"Let apps access your location" and allow Location for your browser (Chrome/Edge). ' +
        'Wi‑Fi should be on. The app will try approximate network location next.'
      )
    case 3:
      return 'Location request timed out. Retry, or use approximate location if offered.'
    default:
      return err.message || 'Could not read location.'
  }
}

function getCurrentPosition(options) {
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, options)
  })
}

function watchPositionOnce(options, maxWaitMs = 30000) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation.watchPosition) {
      reject(new GeoLocationError('unsupported', 'watchPosition not supported'))
      return
    }
    let watchId = null
    let settled = false

    const finish = (fn, value) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      if (watchId != null) navigator.geolocation.clearWatch(watchId)
      fn(value)
    }

    const timer = setTimeout(() => {
      finish(reject, Object.assign(new Error('Location watch timed out'), { code: 3 }))
    }, maxWaitMs)

    watchId = navigator.geolocation.watchPosition(
      (pos) => finish(resolve, pos),
      (err) => finish(reject, err),
      options,
    )
  })
}

async function checkGeolocationPermission() {
  if (!navigator.permissions?.query) return 'unknown'
  try {
    const status = await navigator.permissions.query({ name: 'geolocation' })
    return status.state
  } catch {
    return 'unknown'
  }
}

/**
 * Try several GPS strategies (watchPosition often works when getCurrentPosition fails on Windows).
 * @returns {Promise<GeolocationPosition>}
 */
export async function requestDeviceLocation() {
  if (!navigator.geolocation) {
    throw new GeoLocationError('unsupported', 'Geolocation is not supported in this browser.')
  }
  if (!window.isSecureContext) {
    throw new GeoLocationError(
      'insecure',
      'Location needs a secure page. Open the app via http://localhost:5173 (not http://192.168.x.x).',
    )
  }

  const perm = await checkGeolocationPermission()
  if (perm === 'denied') {
    throw Object.assign(new Error('Permission denied'), { code: 1 })
  }

  const attempts = [
    () => watchPositionOnce({ enableHighAccuracy: false, maximumAge: 600000, timeout: 60000 }, 28000),
    () => getCurrentPosition({ enableHighAccuracy: false, maximumAge: 600000, timeout: 25000 }),
    () => watchPositionOnce({ enableHighAccuracy: true, maximumAge: 0, timeout: 60000 }, 35000),
    () => getCurrentPosition({ enableHighAccuracy: true, maximumAge: 0, timeout: 30000 }),
  ]

  let lastErr = null
  for (const attempt of attempts) {
    try {
      return await attempt()
    } catch (err) {
      lastErr = err
    }
  }
  throw lastErr || Object.assign(new Error('Location unavailable'), { code: 2 })
}
