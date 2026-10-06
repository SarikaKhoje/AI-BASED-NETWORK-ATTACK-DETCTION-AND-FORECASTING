// All calls go through Vite proxy /api → http://127.0.0.1:8000
const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `GET ${path} failed: ${res.status}`)
  }
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res.json()
}

async function uploadCsv(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload-csv`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Upload failed')
  }
  return res.json()
}

export const api = {
  health:     ()      => get('/health'),
  dashboard:  (mode)  => get(`/dashboard?mode=${mode}`),
  forecast:   (idx)   => get(`/forecast?window_index=${idx ?? -1}`),
  detect:     (feats) => post('/detect',  { features: feats }),
  risk:       (body)  => post('/risk',    body),
  explain:    (feats) => post('/explain', { features: feats }),
  liveStatus: ()      => get('/live-status'),
  liveExplanation: () => get('/live-explanation'),
  uploadCsv,
}
