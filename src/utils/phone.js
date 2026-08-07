/** Normalize 10-digit Indian mobile to +91XXXXXXXXXX for API calls. */
export function normalizeIndianPhone(value) {
  const raw = String(value || '').replace(/[\s\-()]/g, '').trim()
  if (!raw) return ''

  let digits = raw
  if (digits.startsWith('+91')) digits = digits.slice(3)
  else if (digits.startsWith('91') && digits.length === 12) digits = digits.slice(2)
  else if (digits.startsWith('0') && digits.length === 11) digits = digits.slice(1)

  if (!/^[6-9]\d{9}$/.test(digits)) {
    throw new Error('Enter a valid 10-digit Indian mobile number (starts with 6, 7, 8, or 9).')
  }
  return `+91${digits}`
}

/** Keep only digits, max 10 — for controlled phone inputs. */
export function digitsOnlyPhoneInput(value) {
  return String(value || '').replace(/\D/g, '').slice(0, 10)
}

export function isValidIndianMobile10(value) {
  return /^[6-9]\d{9}$/.test(digitsOnlyPhoneInput(value))
}

export function validateEmailFormat(value) {
  const email = String(value || '').trim()
  if (!email) return ''
  if (!email.includes('@')) {
    throw new Error('Enter a valid email address (must contain @).')
  }
  const [, domain] = email.split('@')
  if (!domain || !domain.includes('.')) {
    throw new Error('Enter a valid email address (e.g. name@example.com).')
  }
  return email.toLowerCase()
}
