import { BarChart3, Bot, Database, FileText, Info, ScanSearch, Table2 } from 'lucide-react'
import checkiaIcon from '../assets/checkia-icon.png'

const items = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'cases', label: 'Casos', icon: Table2 },
  { id: 'hackia', label: 'HackIAthon', icon: ScanSearch },
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
          <div className="grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-lg bg-white shadow-soft">
            <img src={checkiaIcon} alt="CheckIA" className="h-full w-full object-contain" />
          </div>
          <h1 className="text-xl font-bold tracking-normal">CheckIA</h1>
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
      </div>
    </aside>
  )
}
