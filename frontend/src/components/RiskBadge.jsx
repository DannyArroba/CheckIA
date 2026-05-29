export default function RiskBadge({ level }) {
  const map = {
    Bajo: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    Medio: 'bg-amber-100 text-amber-800 border-amber-200',
    Alto: 'bg-red-100 text-red-800 border-red-200',
    Critico: 'bg-rose-200 text-rose-950 border-rose-300'
  }
  return (
    <span className={`inline-flex min-w-20 justify-center rounded-full border px-3 py-1 text-xs font-bold ${map[level] || map.Bajo}`}>
      {level}
    </span>
  )
}
