import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import Header from './components/Header.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Cases from './pages/Cases.jsx'
import Agent from './pages/Agent.jsx'
import DataLab from './pages/DataLab.jsx'
import Reports from './pages/Reports.jsx'
import About from './pages/About.jsx'

const pages = {
  dashboard: Dashboard,
  cases: Cases,
  agent: Agent,
  data: DataLab,
  reports: Reports,
  about: About
}

export default function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [compact, setCompact] = useState(false)
  const Page = pages[activePage]

  useEffect(() => {
    const onResize = () => setCompact(window.innerWidth < 900)
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  return (
    <div className="min-h-screen bg-mist text-slate-900">
      <Sidebar activePage={activePage} setActivePage={setActivePage} compact={compact} />
      <main className={`${compact ? 'pl-0' : 'pl-72'} min-h-screen transition-all`}>
        <Header activePage={activePage} />
        <div className="px-4 pb-8 pt-4 sm:px-6 lg:px-8">
          <Page setActivePage={setActivePage} />
        </div>
      </main>
    </div>
  )
}
