/**
 * Soft wave between illustration panel and white form (Spacer-style split).
 */
export default function AuthWaveBridge() {
  return (
    <div className="auth-wave-bridge" aria-hidden="true">
      <svg viewBox="0 0 72 800" preserveAspectRatio="none" className="auth-wave-svg">
        <path
          fill="#ffffff"
          d="M72 0v800H0Q40 400 0 0H72z"
        />
      </svg>
    </div>
  )
}
