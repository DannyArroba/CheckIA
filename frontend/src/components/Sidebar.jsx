import { BarChart3, Bot, Database, FileText, Info, ShieldCheck, Table2 } from 'lucide-react'

const items = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'cases', label: 'Casos', icon: Table2 },
  { id: 'agent', label: 'Agente IA', icon: Bot },
  { id: 'data', label: 'Datos', icon: Database },
  { id: 'reports', label: 'Reportes', icon: FileText },
  { id: 'about', label: 'Acerca de', icon: Info }
]

export default function Sidebar({ activePage, setActivePage, compact }) {
  return (
    <aside className={`${compact ? 'relative w-full' : 'fixed inset-y-0 left-0 w-72'} z-20 bg-ink text-white`}>
      <div className="flex h-full flex-col">
        <div className="flex items-center gap-3 px-6 py-6">
          <div className="grid h-11 w-11 place-items-center rounded-lg bg-electric">
            <ShieldCheck size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-normal">CheckIA</h1>
            <p className="text-xs text-blue-100">Asistente inteligente para revisión de siniestros</p>
          </div>
        </div>
        <nav className={`${compact ? 'flex overflow-x-auto px-3 pb-4' : 'space-y-2 px-4'}`}>
          {items.map((item) => {
            const Icon = item.icon
            const active = activePage === item.id
            return (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                className={`flex min-h-11 items-center gap-3 rounded-lg px-4 text-sm font-semibold transition ${compact ? 'mr-2' : 'w-full'} ${
                  active ? 'bg-white text-ink shadow-soft' : 'text-blue-100 hover:bg-white/10 hover:text-white'
                }`}
              >
                <Icon size={18} />
                {item.label}
              </button>
            )
          })}
        </nav>
        {!compact && (
          <div className="mt-auto px-6 py-6 text-xs leading-5 text-blue-100">
            Alertas explicables para priorizar revisión humana. Sin acusaciones ni decisiones automáticas.
          </div>
        )}
      </div>
    </aside>
  )
}
