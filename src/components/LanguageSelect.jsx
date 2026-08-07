import { COMPLAINT_LANGUAGES } from '../utils/languages'

export default function LanguageSelect({ id, className = 'select', value, onChange, label = 'Language' }) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} className={className} value={value} onChange={onChange}>
        {COMPLAINT_LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.name}
          </option>
        ))}
      </select>
    </div>
  )
}
