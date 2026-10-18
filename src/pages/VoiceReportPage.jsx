import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiMultipart } from '../api/client'
import LanguageSelect from '../components/LanguageSelect'
import { bufferToFile, enqueueVoiceJob, listPendingJobs, removeJob } from '../offline/voiceQueue'

function pickRecorderMime() {
  const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
  if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported) {
    for (const t of types) {
      if (MediaRecorder.isTypeSupported(t)) return t
    }
  }
  return 'audio/webm'
}

function extForMime(mime) {
  const m = (mime || '').split(';')[0].toLowerCase()
  if (m.includes('mp4')) return 'm4a'
  return 'webm'
}

/** Elapsed ms → M:SS.hh (hundredths tick smoothly at 10fps+). */
function formatElapsed(ms) {
  const clamped = Math.max(0, ms)
  const totalSec = Math.floor(clamped / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  const centi = Math.floor((clamped % 1000) / 10)
  return `${m}:${String(s).padStart(2, '0')}.${String(centi).padStart(2, '0')}`
}

export default function VoiceReportPage() {
  const { access } = useAuth()
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [language, setLanguage] = useState('hi')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState('')
  const [queue, setQueue] = useState([])
const [recording, setRecording] = useState(false)
const [elapsedMs, setElapsedMs] = useState(0)
const MIN_RECORD_MS = 3000
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const tickRef = useRef(null)
  const waveCanvasRef = useRef(null)
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const waveRafRef = useRef(null)
  const freqDataRef = useRef(null)
  const recordStartRef = useRef(0)
  const recordingActiveRef = useRef(false)

  function disposeLiveMonitoring() {
    recordingActiveRef.current = false
    if (waveRafRef.current) {
      cancelAnimationFrame(waveRafRef.current)
      waveRafRef.current = null
    }
    if (tickRef.current) {
      clearInterval(tickRef.current)
      tickRef.current = null
    }
    analyserRef.current = null
    const ctx = audioContextRef.current
    audioContextRef.current = null
    if (ctx && ctx.state !== 'closed') {
      ctx.close().catch(() => {})
    }
  }

  useEffect(() => {
    return () => {
      disposeLiveMonitoring()
      streamRef.current?.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
  }, [])

  async function refreshQueue() {
    setQueue(await listPendingJobs())
  }

  useEffect(() => {
    queueMicrotask(() => {
      void refreshQueue()
    })
  }, [])

  async function transcribe(e) {
    e.preventDefault()
    setError('')
    if (!file) {
      setError('Choose an audio file first.')
      return
    }
    if (file.size < 4000) {
      setError('Recording is too short. Speak for at least 3 seconds and try again.')
      return
    }
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('audio_file', file)
      fd.append('language', language)
      const data = await apiMultipart('/voice/transcribe/', fd, access)
      const t = (data.transcript || '').trim()
      const voiceStub = !!data.stub_transcript
      const transcriptionFailed = !!data.transcription_failed
      const englishTranslation = data.english_translation || ''

      if (voiceStub) {
        setError('Speech-to-text is not installed on the backend yet. Your recording was received, but no transcript was created. Use “Skip voice — type complaint instead” to continue.')
        return
      }

      if (transcriptionFailed && !voiceStub) {
        setError(
          data.user_message ||
            'Could not understand the recording. Speak for at least 3 seconds in a quiet room and try again.',
        )
        return
      }

      if (!t && !voiceStub) {
        setError('No speech detected. Record again or type your complaint on the New complaint page.')
        return
      }

      const detected =
        data.language && String(data.language).length <= 5 && String(data.language).length >= 2 ? String(data.language) : ''
      // Keep the language the user picked (Hindi, Tamil, …) — do not override with Whisper detect.
      const langForForm = language || detected
      setPreview(t)
      try {
        sessionStorage.setItem(
          'awaaz_voice_new_complaint',
          JSON.stringify({
            transcript: t,
            englishTranslation,
            lang: langForForm,
            voiceStub,
            transcriptionFailed,
            at: Date.now(),
          }),
        )
      } catch {
        /* quota / private mode */
      }
      navigate('/complaints/new', {
        state: {
          transcript: t,
          englishTranslation,
          lang: langForForm,
          voiceStub,
          transcriptionFailed,
          fromVoice: true,
        },
      })
    } catch (err) {
      setError(err.message || 'Transcription failed')
    } finally {
      setBusy(false)
    }
  }

  async function saveOffline() {
    setError('')
    if (!file) {
      setError('Choose an audio file to queue for sync.')
      return
    }
    try {
      await enqueueVoiceJob({ language, file })
      setFile(null)
      await refreshQueue()
    } catch (e) {
      setError(e.message || 'Could not save offline')
    }
  }

  async function syncJob(job) {
    setBusy(true)
    setError('')
    try {
      const blobFile = bufferToFile(job)
      const fd = new FormData()
      fd.append('audio_file', blobFile)
      fd.append('language', job.language || 'hi')
      const data = await apiMultipart('/voice/transcribe/', fd, access)
      const t = (data.transcript || '').trim()
      const voiceStub = !!data.stub_transcript
      const transcriptionFailed = !!data.transcription_failed
      const englishTranslation = data.english_translation || ''
      if (voiceStub) {
        setError('Speech-to-text is not installed on the backend yet. This recording remains in your offline queue; use “Skip voice — type complaint instead” to continue.')
        return
      }
      if (transcriptionFailed && !voiceStub) {
        setError(data.user_message || 'Could not transcribe queued recording. Try again.')
        return
      }
      await removeJob(job.id)
      await refreshQueue()
      const detected =
        data.language && String(data.language).length <= 5 && String(data.language).length >= 2 ? String(data.language) : ''
      const lang = job.language || detected || 'hi'
      try {
        sessionStorage.setItem(
          'awaaz_voice_new_complaint',
          JSON.stringify({ transcript: t, englishTranslation, lang, voiceStub, transcriptionFailed, at: Date.now() }),
        )
      } catch {
        /* ignore */
      }
      navigate('/complaints/new', {
        state: { transcript: t, englishTranslation, lang, voiceStub, transcriptionFailed, fromVoice: true },
      })
    } catch (err) {
      setError(err.message || 'Sync failed — try again when online.')
    } finally {
      setBusy(false)
    }
  }

  async function dropJob(id) {
    await removeJob(id)
    await refreshQueue()
  }

  async function startRecording() {
    if (recording || busy) return
    setError('')
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone recording is not supported in this browser.')
      return
    }
    if (typeof MediaRecorder === 'undefined') {
      setError('MediaRecorder is not available. Try another browser or upload a file.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      })
      streamRef.current = stream
      const mime = pickRecorderMime()
      chunksRef.current = []
      const mr = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
      mediaRecorderRef.current = mr
      mr.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data)
      }
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        streamRef.current = null
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || mime || 'audio/webm' })
        chunksRef.current = []
        const durationMs = performance.now() - recordStartRef.current
        if (blob.size < 4000 || durationMs < MIN_RECORD_MS) {
          setError('Recording was too short. Speak for at least 3 seconds in a quiet place, then stop.')
          return
        }
        const ext = extForMime(mr.mimeType || mime)
        const name = `voice-recording-${Date.now()}.${ext}`
        setFile(new File([blob], name, { type: blob.type || 'audio/webm' }))
      }
      setElapsedMs(0)
      recordStartRef.current = performance.now()
      recordingActiveRef.current = true

      const Ctx = window.AudioContext || window.webkitAudioContext
      if (Ctx) {
        const audioCtx = new Ctx()
        audioContextRef.current = audioCtx
        if (audioCtx.state === 'suspended') await audioCtx.resume()
        const source = audioCtx.createMediaStreamSource(stream)
        const analyser = audioCtx.createAnalyser()
        analyser.fftSize = 256
        analyser.smoothingTimeConstant = 0.62
        source.connect(analyser)
        analyserRef.current = analyser
        freqDataRef.current = new Uint8Array(analyser.frequencyBinCount)

        const drawWave = () => {
          if (!recordingActiveRef.current) return
          const canvas = waveCanvasRef.current
          const node = analyserRef.current
          const data = freqDataRef.current
          if (!canvas || !node || !data) {
            waveRafRef.current = requestAnimationFrame(drawWave)
            return
          }
          node.getByteFrequencyData(data)
          const rect = canvas.getBoundingClientRect()
          const cssW = Math.max(240, rect.width)
          const cssH = 72
          const dpr = Math.min(window.devicePixelRatio || 1, 2)
          const w = Math.floor(cssW * dpr)
          const h = Math.floor(cssH * dpr)
          if (canvas.width !== w || canvas.height !== h) {
            canvas.width = w
            canvas.height = h
          }
          const ctx2 = canvas.getContext('2d')
          if (!ctx2) {
            waveRafRef.current = requestAnimationFrame(drawWave)
            return
          }
          ctx2.clearRect(0, 0, w, h)
          ctx2.fillStyle = 'rgba(45, 106, 79, 0.07)'
          ctx2.fillRect(0, 0, w, h)
          const barCount = 44
          const step = Math.max(1, Math.floor(data.length / barCount))
          const barW = w / barCount - dpr * 0.8
          for (let i = 0; i < barCount; i++) {
            let sum = 0
            for (let j = 0; j < step; j++) sum += data[i * step + j]
            const norm = (sum / step) / 255
            const barH = Math.max(dpr * 2, norm * h * 0.9)
            const x = (i / barCount) * w + dpr * 0.35
            const y = h - barH
            const g = ctx2.createLinearGradient(0, y, 0, h)
            g.addColorStop(0, '#3d8a67')
            g.addColorStop(1, '#2d6a4f')
            ctx2.fillStyle = g
            ctx2.fillRect(x, y, barW, barH)
          }
          waveRafRef.current = requestAnimationFrame(drawWave)
        }
        waveRafRef.current = requestAnimationFrame(drawWave)
      }

      tickRef.current = setInterval(() => {
        setElapsedMs(Math.round(performance.now() - recordStartRef.current))
      }, 100)

      mr.start(250)
      setRecording(true)
    } catch (e) {
      disposeLiveMonitoring()
      streamRef.current?.getTracks().forEach((t) => t.stop())
      streamRef.current = null
      const msg = e instanceof Error ? e.message : String(e)
      if (/NotAllowedError|PermissionDenied/i.test(msg)) {
        setError('Microphone permission was denied. Allow the mic for this site and try again.')
      } else {
        setError(msg || 'Could not start microphone.')
      }
    }
  }

  function stopRecording() {
    const mr = mediaRecorderRef.current
    mediaRecorderRef.current = null
    recordingActiveRef.current = false
    disposeLiveMonitoring()
    setElapsedMs(0)
    setRecording(false)
    if (mr && mr.state !== 'inactive') {
      try {
        mr.stop()
      } catch {
        /* ignore */
      }
    }
  }

  function clearRecording() {
    stopRecording()
    setFile(null)
    setElapsedMs(0)
  }

  return (
    <div className="container" style={{ maxWidth: 560 }}>
      <div className="section-tag">Voice-first</div>
      <h1 className="page-title">Voice complaint</h1>
      <p className="muted" style={{ marginBottom: 24 }}>
        Record from your microphone, upload a file, or queue for offline sync (IndexedDB). After transcribe, you’re taken
        to <strong>New complaint</strong> with the text filled in. Real speech-to-text requires Whisper to be installed
        on the backend; if it is unavailable, the page will tell you to continue by typing instead.
      </p>
      <form className="glass-card" onSubmit={transcribe}>
        {error ? <div className="error-banner">{error}</div> : null}
        <LanguageSelect
          id="voice-lang"
          label="Speak in"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        />
        <p className="muted" style={{ fontSize: 13, marginTop: -8, marginBottom: 16, lineHeight: 1.45 }}>
          Supported: <strong>Hindi</strong>, <strong>English</strong>, <strong>Tamil</strong>, <strong>Marathi</strong>.
          Record at least <strong>3 seconds</strong> in a quiet room. You can edit the text on the next screen.
        </p>
        <div className="field">
          <label>Live recording</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
            {!recording ? (
              <button type="button" className="btn-secondary" onClick={startRecording} disabled={busy}>
                Start recording
              </button>
            ) : (
              <button type="button" className="btn-primary" onClick={stopRecording} disabled={busy}>
                Stop &amp; attach
              </button>
            )}
            {file && !recording ? (
              <button type="button" className="btn-ghost" onClick={clearRecording} disabled={busy}>
                Clear audio
              </button>
            ) : null}
          </div>
          {recording ? (
            <div className="voice-rec-live-panel" role="region" aria-label="Recording in progress">
              <div className="voice-rec-live-header">
                <span className="voice-rec-live-badge">
                  <span className="voice-rec-live-dot" aria-hidden="true" />
                  Live
                </span>
                <span className="voice-rec-live-sub">Live input · level meter</span>
              </div>
              <div className="voice-rec-live-timer" aria-live="polite" aria-atomic="true">
                {formatElapsed(elapsedMs)}
              </div>
              <div className="voice-rec-live-wave-wrap">
                <canvas ref={waveCanvasRef} className="voice-rec-live-wave" aria-hidden="true" />
              </div>
              <p className="muted voice-rec-live-hint">
                Bars react to your voice in real time. When you are done, press <strong>Stop &amp; attach</strong> — the
                clip is saved as your upload (WebM/Opus or MP4 where the browser allows).
              </p>
            </div>
          ) : file ? (
            <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>
              Ready: <strong>{file.name}</strong> ({Math.round(file.size / 1024)} KB)
            </p>
          ) : (
            <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>
              Or choose a file below — recording and file upload use the same transcribe step.
            </p>
          )}
        </div>
        <div className="field">
          <label>Audio file (optional if you recorded above)</label>
          <input
            type="file"
            accept="audio/*,.mp3,.wav,.m4a,.webm,.ogg"
            className="input"
            disabled={recording}
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>
        <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={busy || recording}>
          {busy ? 'Transcribing…' : 'Transcribe & continue'}
        </button>
        <div style={{ marginTop: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button type="button" className="btn-secondary" onClick={saveOffline} disabled={busy}>
            Queue for offline sync
          </button>
        </div>
        <p className="muted" style={{ marginTop: 14 }}>
          <Link to="/complaints/new">Skip voice — type complaint instead</Link>
        </p>
        {preview ? (
          <p style={{ marginTop: 16, fontSize: 14 }}>
            <strong>Last transcript:</strong> {preview}
          </p>
        ) : null}
      </form>

      {queue.length > 0 ? (
        <div className="glass-card" style={{ marginTop: 20 }}>
          <h3 style={{ marginBottom: 10 }}>Offline queue ({queue.length})</h3>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {queue.map((job) => (
              <li
                key={job.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 8,
                  padding: '10px 0',
                  borderBottom: '1px solid var(--border-color)',
                }}
              >
                <span className="muted" style={{ fontSize: 14 }}>
                  {job.name} · {new Date(job.createdAt).toLocaleString()}
                </span>
                <span>
                  <button type="button" className="btn-secondary" style={{ padding: '6px 10px' }} onClick={() => syncJob(job)} disabled={busy}>
                    Sync now
                  </button>{' '}
                  <button type="button" className="btn-ghost" style={{ padding: '6px 10px' }} onClick={() => dropJob(job.id)}>
                    Remove
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
