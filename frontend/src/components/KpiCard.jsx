export default function KpiCard({ title, value, helper, tone = 'blue', icon: Icon }) {
  const tones = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-emerald-50 text-emerald-700',
    yellow: 'bg-amber-50 text-amber-700',
    red: 'bg-red-50 text-red-700',
    slate: 'bg-slate-100 text-slate-700'
  }
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-ink">{value}</p>
        </div>
        {Icon && <div className={`grid h-10 w-10 place-items-center rounded-lg ${tones[tone]}`}><Icon size={20} /></div>}
      </div>
      {helper && <p className="mt-3 text-sm text-slate-500">{helper}</p>}
    </div>
  )
}
