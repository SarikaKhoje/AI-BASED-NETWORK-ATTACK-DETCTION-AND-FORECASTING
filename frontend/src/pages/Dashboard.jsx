import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../services/api'
import StatCard from '../components/StatCard'
import AttackChart from '../components/AttackChart'
import SHAPChart from '../components/SHAPChart'

const RISK_COLOR = { CRITICAL: 'red', HIGH: 'red', MEDIUM: 'yellow', LOW: 'green' }

export default function Dashboard() {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [mode, setMode]         = useState('demo')
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef()

  // ── Load demo/live dashboard data ──────────────────────
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await api.dashboard(mode)
      setData(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [mode])

  useEffect(() => { load() }, [load])

  // ── Poll /live-status every 5 s when in live mode ──────
  useEffect(() => {
    if (mode !== 'live') return
    const id = setInterval(async () => {
      try {
        const s = await api.liveStatus()
        if (s.available && s.data) setData(s.data)
      } catch (_) {}
    }, 5000)
    return () => clearInterval(id)
  }, [mode])

  // ── Handle CSV upload ──────────────────────────────────
  const handleFile = async (file) => {
    if (!file) return
    if (!file.name.endsWith('.csv')) {
      setUploadMsg({ ok: false, text: 'Please upload a .csv file (CICFlowMeter output).' })
      return
    }
    setUploading(true)
    setUploadMsg(null)
    try {
      const result = await api.uploadCsv(file)
      setData(result)
      setMode('live')
      setUploadMsg({
        ok: true,
        text: `✓ Processed ${result.summary?.total_flows?.toLocaleString()} flows — ${result.summary?.attack_flows?.toLocaleString()} attacks detected.`,
      })
    } catch (e) {
      setUploadMsg({ ok: false, text: `Upload failed: ${e.message}` })
    } finally {
      setUploading(false)
    }
  }

  const onFileInput  = (e) => handleFile(e.target.files[0])
  const onDrop       = (e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]) }
  const onDragOver   = (e) => { e.preventDefault(); setDragOver(true) }
  const onDragLeave  = () => setDragOver(false)

  const det  = data?.detection
  const fore = data?.forecast
  const risk = data?.risk
  const expl = data?.explanation
  const isLiveData = mode === 'live' && data?.summary

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">

      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">AI Network Security Dashboard</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Random Forest Detection · Gradient Boosting Forecast · Rule-Based Risk Engine · SHAP
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex rounded-lg overflow-hidden border border-gray-700">
            {['demo', 'live'].map(m => (
              <button key={m} onClick={() => setMode(m)}
                className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                  mode === m ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}>
                {m.toUpperCase()}
              </button>
            ))}
          </div>
          <button onClick={load} disabled={loading}
            className="px-4 py-1.5 bg-blue-700 hover:bg-blue-600 disabled:opacity-50 rounded-lg text-sm font-medium">
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* ── Mode badge ── */}
      {mode === 'demo' && (
        <div className="mb-4 inline-flex items-center gap-2 bg-yellow-900/40 border border-yellow-700 text-yellow-300 text-xs px-3 py-1.5 rounded-full">
          <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
          DEMO MODE — Historical CIC-IDS2017 Traffic
        </div>
      )}
      {mode === 'live' && (
        <div className="mb-4 inline-flex items-center gap-2 bg-green-900/40 border border-green-700 text-green-300 text-xs px-3 py-1.5 rounded-full">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          LIVE MODE — {isLiveData ? data.summary.filename : 'Waiting for upload…'}
        </div>
      )}

      {error && (
        <div className="mb-4 bg-red-900/40 border border-red-700 text-red-300 text-sm px-4 py-3 rounded-lg">
          ⚠ {error} — Is the FastAPI backend running?
        </div>
      )}

      {/* ── LIVE UPLOAD PANEL ── */}
      <div className="mb-6 bg-gray-900 rounded-xl border border-gray-700 p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-1 uppercase tracking-wide">
          Live Traffic Upload
        </h2>
        <p className="text-xs text-gray-500 mb-4">
          Capture network traffic with <span className="text-blue-400">Wireshark</span>, convert the PCAP to CSV using{' '}
          <span className="text-blue-400">CICFlowMeter</span>, then upload the CSV here.
          The full pipeline runs automatically: Random Forest → Forecast → Risk → SHAP.
        </p>

        {/* Pipeline diagram */}
        <div className="flex flex-wrap items-center gap-1 text-xs text-gray-400 mb-4 font-mono">
          {['Wireshark/PCAP', '→', 'CICFlowMeter', '→', 'CSV Upload ↑', '→', 'Random Forest', '→', 'Forecast', '→', 'Risk Engine', '→', 'Dashboard'].map((s, i) => (
            <span key={i} className={s === '→' ? 'text-gray-600' : s.includes('Upload') ? 'text-green-400 font-semibold' : 'bg-gray-800 px-2 py-0.5 rounded'}>
              {s}
            </span>
          ))}
        </div>

        {/* Drop zone */}
        <div
          onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
          onClick={() => fileRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            dragOver ? 'border-blue-500 bg-blue-950/30' : 'border-gray-700 hover:border-gray-500'
          }`}>
          <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={onFileInput} />
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-blue-400">Processing through pipeline…</p>
            </div>
          ) : (
            <>
              <p className="text-3xl mb-2">📂</p>
              <p className="text-sm text-gray-300 font-medium">Drop CICFlowMeter CSV here</p>
              <p className="text-xs text-gray-500 mt-1">or click to browse · .csv files only</p>
            </>
          )}
        </div>

        {uploadMsg && (
          <div className={`mt-3 text-sm px-4 py-2 rounded-lg ${
            uploadMsg.ok
              ? 'bg-green-900/40 border border-green-700 text-green-300'
              : 'bg-red-900/40 border border-red-700 text-red-300'
          }`}>
            {uploadMsg.text}
          </div>
        )}

        {/* Live summary stats */}
        {isLiveData && (
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            {[
              { label: 'Total Flows',   value: data.summary.total_flows?.toLocaleString(),  color: 'text-white' },
              { label: 'Attack Flows',  value: data.summary.attack_flows?.toLocaleString(), color: 'text-red-400' },
              { label: 'Normal Flows',  value: data.summary.normal_flows?.toLocaleString(), color: 'text-blue-400' },
              { label: 'Attack Ratio',  value: `${(data.summary.attack_ratio * 100).toFixed(1)}%`, color: 'text-yellow-400' },
            ].map(s => (
              <div key={s.label} className="bg-gray-800 rounded-lg p-3">
                <p className="text-gray-500 mb-0.5">{s.label}</p>
                <p className={`font-bold text-base ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* How-to guide */}
        <details className="mt-4">
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">
            How to get a CICFlowMeter CSV from a PCAP file ▸
          </summary>
          <ol className="mt-2 text-xs text-gray-400 space-y-1 list-decimal list-inside">
            <li>Capture traffic in Wireshark → File → Export as <code className="bg-gray-800 px-1 rounded">.pcap</code></li>
            <li>Download CICFlowMeter from <span className="text-blue-400">github.com/ahlashkari/CICFlowMeter</span></li>
            <li>Run: <code className="bg-gray-800 px-1 rounded">java -jar CICFlowMeter.jar &lt;input.pcap&gt; &lt;output_folder&gt;</code></li>
            <li>Upload the generated <code className="bg-gray-800 px-1 rounded">.csv</code> file here</li>
            <li>Dashboard updates automatically with real predictions</li>
          </ol>
        </details>
      </div>

      {/* ── Top stat cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Current Attack"
          value={det?.attack_type ?? '—'}
          sub={det ? `Confidence: ${(det.confidence * 100).toFixed(1)}%` : undefined}
          color={det?.is_attack ? 'red' : 'green'}
        />
        <StatCard
          title="Future Forecast"
          value={fore ? fore.predicted_attack_count.toLocaleString() : '—'}
          sub="Expected attacks · Next 5 min"
          color="purple"
        />
        <StatCard
          title="Risk Score"
          value={risk?.risk_score ?? '—'}
          sub="Rule-Based Risk Assessment Engine"
          color={RISK_COLOR[risk?.risk_level] ?? 'blue'}
        />
        <StatCard
          title="Risk Level"
          value={risk?.risk_level ?? '—'}
          badge={risk?.risk_level}
          color={RISK_COLOR[risk?.risk_level] ?? 'blue'}
        />
      </div>

      {/* ── Attack Activity Chart ── */}
      <div className="bg-gray-900 rounded-xl p-5 mb-6 border border-gray-800">
        <h2 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wide">
          Attack Activity — 5-Minute Windows
        </h2>
        <AttackChart data={data?.attack_chart} />
      </div>

      {/* ── Detection + Forecast detail ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">Detection</h2>
          {det ? (
            <dl className="space-y-2 text-sm">
              <Row label="Attack Type"     value={det.attack_type} />
              <Row label="Confidence"      value={`${(det.confidence * 100).toFixed(2)}%`} />
              <Row label="Is Attack"       value={det.is_attack ? '⚠ YES' : '✓ BENIGN'} />
              <Row label="Current Attacks" value={fore?.current_attack_count?.toLocaleString() ?? '—'} />
              <Row label="Attack Ratio"    value={fore ? `${(fore.attack_ratio * 100).toFixed(1)}%` : '—'} />
            </dl>
          ) : <p className="text-gray-500 text-sm">No detection data.</p>}
        </div>

        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">Forecast</h2>
          {fore ? (
            <dl className="space-y-2 text-sm">
              <Row label="Predicted Attacks"   value={fore.predicted_attack_count.toLocaleString()} />
              <Row label="Window Start"        value={fore.forecast_window_start} />
              <Row label="Window End"          value={fore.forecast_window_end} />
              <Row label="Forecast Risk Label" value={fore.forecast_risk_label} />
              <Row label="Data Source"         value={fore.data_source} small />
            </dl>
          ) : <p className="text-gray-500 text-sm">No forecast data.</p>}
        </div>
      </div>

      {/* ── SHAP Explanation ── */}
      <div className="bg-gray-900 rounded-xl p-5 mb-6 border border-gray-800">
        <h2 className="text-sm font-semibold text-gray-300 mb-1 uppercase tracking-wide">
          SHAP Explanation
        </h2>
        <p className="text-xs text-gray-500 mb-4">
          Why did the Random Forest classify this traffic as{' '}
          <span className="text-yellow-400">{expl?.prediction ?? '—'}</span>?
          (Red = pushes toward attack · Blue = pushes toward benign)
        </p>
        <SHAPChart features={expl?.top_features} />
      </div>

      {/* ── Recent Windows Table ── */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">
          Recent Traffic Windows
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-gray-300">
            <thead>
              <tr className="border-b border-gray-700 text-gray-500 uppercase">
                {['Time', 'Total Flows', 'Attack Flows', 'Normal Flows', 'Attack Ratio', 'Forecast Next'].map(h => (
                  <th key={h} className="pb-2 pr-4 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.recent_windows ?? []).map((w, i) => (
                <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/40">
                  <td className="py-1.5 pr-4">{w.time?.slice(11, 16)}</td>
                  <td className="py-1.5 pr-4">{(w.attack_flows + w.normal_flows).toLocaleString()}</td>
                  <td className="py-1.5 pr-4 text-red-400">{w.attack_flows?.toLocaleString()}</td>
                  <td className="py-1.5 pr-4 text-blue-400">{w.normal_flows?.toLocaleString()}</td>
                  <td className="py-1.5 pr-4">{(w.attack_ratio * 100).toFixed(1)}%</td>
                  <td className="py-1.5 pr-4 text-yellow-400">{w.predicted_next?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-center text-xs text-gray-600 mt-6">
        AI-Based Network Attack Detection and Forecasting · CIC-IDS2017 · College Project Demo
      </p>
    </div>
  )
}

function Row({ label, value, small }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-gray-500">{label}</dt>
      <dd className={`text-right font-medium ${small ? 'text-gray-400 text-xs' : 'text-white'}`}>{value}</dd>
    </div>
  )
}
