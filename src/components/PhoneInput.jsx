import { digitsOnlyPhoneInput } from '../utils/phone'

export default function PhoneInput({ id, value, onChange, className = 'input input-auth-line', required = true }) {
  return (
    <div className="phone-input-wrap" style={{ display: 'flex', gap: 8, alignItems: 'stretch' }}>
      <span
        className="phone-prefix"
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 12px',
          borderRadius: 8,
          border: '1px solid var(--border-subtle, #d1d5db)',
          background: 'var(--surface-muted, #f3f4f6)',
          fontWeight: 600,
          fontSize: 14,
          whiteSpace: 'nowrap',
        }}
      >
        +91
      </span>
      <input
        id={id}
        className={className}
        type="tel"
        inputMode="numeric"
        autoComplete="tel-national"
        placeholder="9876543210"
        maxLength={10}
        value={value}
        onChange={(e) => onChange(digitsOnlyPhoneInput(e.target.value))}
        required={required}
        style={{ flex: 1 }}
      />
    </div>
  )
}
