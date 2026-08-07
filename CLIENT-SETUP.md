# Nagrik Awaaz — Frontend setup (client)

## Requirements

- **Node.js 18+** and npm
- Backend running at http://127.0.0.1:8000 (see `awaaz-backend/CLIENT-SETUP.md`)

## Quick start

```powershell
cd nagrik-awaaz-app
npm install
copy .env.example .env.local
npm run dev
```

Open: http://127.0.0.1:5173

`npm run dev` proxies `/api` → `http://127.0.0.1:8000` (set `VITE_BACKEND_URL` in `.env.local` if needed).

## Branding images

Place these files in `public/branding/` (if not included in zip):

- `nagrik-awaaz-logo.png`
- `hero-wide.png`
- `voice-feature.png`
- `officer-desk.png`
- `trust-verification.png`
- `empty-state.png`
- `faq-hero.png`
- `login-hero.png`
- `register-hero.png`

The app works without them; images will simply not show.

## Production build

```powershell
npm run build
npm run preview
```

For preview talking to Django on another port, set in `.env.local`:

```
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Supported languages

Voice + complaints: **Hindi, English, Tamil, Marathi** only.

## Register flow

1. Enter 10-digit mobile → **Send OTP**
2. Use OTP shown in response (demo) or SMS if Twilio configured
3. Complete form → Register
