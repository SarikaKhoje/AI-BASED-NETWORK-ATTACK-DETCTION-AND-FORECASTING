export default function StatCard({ title, value, sub, color = 'blue', badge }) {
  const colors = {
    blue:   'border-blue-500   bg-blue-950   text-blue-300',
    red:    'border-red-500    bg-red-950    text-red-300',
    yellow: 'border-yellow-500 bg-yellow-950 text-yellow-300',
    green:  'border-green-500  bg-green-950  text-green-300',
    purple: 'border-purple-500 bg-purple-950 text-purple-300',
  }
  const riskColors = {
    CRITICAL: 'bg-red-600 text-white',
    HIGH:     'bg-orange-500 text-white',
    MEDIUM:   'bg-yellow-500 text-black',
    LOW:      'bg-green-600 text-white',
  }

  return (
    <div className={`rounded-xl border-l-4 p-4 ${colors[color]} shadow-lg`}>
      <p className="text-xs uppercase tracking-widest opacity-70 mb-1">{title}</p>
      <p className="text-2xl font-bold text-white">{value ?? '—'}</p>
      {sub && <p className="text-xs mt-1 opacity-60">{sub}</p>}
      {badge && (
        <span className={`mt-2 inline-block px-2 py-0.5 rounded text-xs font-semibold ${riskColors[badge] ?? 'bg-gray-600 text-white'}`}>
          {badge}
        </span>
      )}
    </div>
  )
}
