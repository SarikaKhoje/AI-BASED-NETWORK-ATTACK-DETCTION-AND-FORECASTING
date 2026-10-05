import {
  ResponsiveContainer, ComposedChart, Bar, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'

export default function AttackChart({ data }) {
  if (!data || data.length === 0) return <p className="text-gray-500 text-sm">No chart data.</p>

  const formatted = data.map(d => ({
    time: d.time?.slice(11, 16) ?? '',   // HH:MM
    attack: d.attack_flows,
    normal: d.normal_flows,
    forecast: d.predicted_next,
  }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={formatted} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="time" tick={{ fill: '#9ca3af', fontSize: 11 }} />
        <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
          labelStyle={{ color: '#f9fafb' }}
        />
        <Legend wrapperStyle={{ color: '#d1d5db', fontSize: 12 }} />
        <Bar dataKey="attack" name="Attack Flows" fill="#ef4444" opacity={0.85} />
        <Bar dataKey="normal" name="Normal Flows" fill="#3b82f6" opacity={0.6} />
        <Line type="monotone" dataKey="forecast" name="Forecast (next window)" stroke="#facc15" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
