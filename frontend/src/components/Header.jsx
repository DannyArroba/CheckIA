import { Activity, ShieldAlert } from 'lucide-react'

const titles = {
  dashboard: 'Panel de control',
  cases: 'Siniestros analizados',
  agent: 'Agente IA',
  data: 'Datos y entrenamiento',
  reports: 'Reportes ejecutivos',
  about: 'Acerca de CheckIA'
}

export default function Header({ activePage }) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/92 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6 lg:px-8">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-electric">Aseguradora del Sur</p>
          <h2 className="text-2xl font-bold text-ink">{titles[activePage]}</h2>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          <Activity size={17} className="text-emerald-600" />
          Datos sintéticos activos
          <ShieldAlert size={17} className="text-amber-500" />
        </div>
      </div>
    </header>
  )
}
