import {
  ResponsiveContainer, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine,
} from 'recharts'

export default function SHAPChart({ features }) {
  if (!features || features.length === 0)
    return <p className="text-gray-500 text-sm">No SHAP data.</p>

  const data = [...features]
    .sort((a, b) => a.shap_value - b.shap_value)
    .map(f => ({ name: f.feature, value: f.shap_value }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 140, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} />
        <YAxis type="category" dataKey="name" tick={{ fill: '#d1d5db', fontSize: 11 }} width={135} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
          formatter={(v) => [v.toFixed(4), 'SHAP Value']}
        />
        <ReferenceLine x={0} stroke="#6b7280" />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.value >= 0 ? '#ef4444' : '#3b82f6'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
