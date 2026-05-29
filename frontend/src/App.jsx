import { useEffect, useState } from 'react'
import { claimsApi } from './api/claimsApi.js'
import CsvValidationModal from './components/CsvValidationModal.jsx'
import Sidebar from './components/Sidebar.jsx'
import Header from './components/Header.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Cases from './pages/Cases.jsx'
import Hackia from './pages/Hackia.jsx'
import Agent from './pages/Agent.jsx'
import DataLab from './pages/DataLab.jsx'
import Reports from './pages/Reports.jsx'
import About from './pages/About.jsx'

const pages = {
  dashboard: Dashboard,
  cases: Cases,
  hackia: Hackia,
  agent: Agent,
  data: DataLab,
  reports: Reports,
  about: About
}

export default function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [compact, setCompact] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [modal, setModal] = useState(null)
  const Page = pages[activePage]

  useEffect(() => {
    const onResize = () => setCompact(window.innerWidth < 900)
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  async function handleDroppedFiles(files) {
    const list = Array.from(files || [])
    if (!list.length) return
    const excels = list.filter((file) => /\.(xlsx|xlsm|xls)$/i.test(file.name))
    const pdfs = list.filter((file) => /\.pdf$/i.test(file.name))
    const rejected = list.filter((file) => !excels.includes(file) && !pdfs.includes(file))
    try {
      let excelResult = null
      let pdfResult = null
      if (excels[0]) excelResult = await claimsApi.uploadHackiaExcel(excels[0])
      if (pdfs.length) pdfResult = await claimsApi.uploadHackiaPdfs(pdfs)
      const rejectedPdfs = pdfResult?.details?.filter((item) => item.rechazado).length || 0
      setModal({
        type: rejected.length || rejectedPdfs ? 'warning' : 'success',
        title: 'Carga por arrastre procesada',
        body: rejected.length
          ? `${rejected.length} archivo(s) fueron omitidos porque no son Excel ni PDF.`
          : rejectedPdfs
            ? `${rejectedPdfs} PDF(s) fueron omitidos porque no tenían SIN-xxxx ni DOC-xxxx.`
            : 'Los archivos fueron importados y analizados correctamente.',
        stats: [
          { label: 'Excel', value: excelResult ? 1 : 0 },
          { label: 'PDFs procesados', value: pdfResult?.stats?.pdfs_procesados ?? 0 },
          { label: 'Alertas', value: excelResult?.analysis?.alertas_generadas ?? pdfResult?.analysis?.alertas_generadas ?? '-' }
        ]
      })
      setActivePage('hackia')
    } catch (error) {
      setModal({ title: 'No se pudo cargar por arrastre', body: String(error.detail || error.message), type: 'error' })
    }
  }

  return (
    <div
      className="min-h-screen bg-mist text-slate-900"
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={(event) => {
        if (event.currentTarget === event.target) setDragging(false)
      }}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        handleDroppedFiles(event.dataTransfer.files)
      }}
    >
      <Sidebar activePage={activePage} setActivePage={setActivePage} compact={compact} />
      <main className={`${compact ? 'pl-0' : 'pl-72'} min-h-screen transition-all`}>
        <Header activePage={activePage} />
        <div className="px-4 pb-8 pt-4 sm:px-6 lg:px-8">
          <Page setActivePage={setActivePage} />
        </div>
      </main>
      {dragging && (
        <div className="pointer-events-none fixed inset-0 z-50 grid place-items-center bg-ink/40 p-6 backdrop-blur-sm">
          <div className="rounded-lg border border-blue-200 bg-white px-8 py-6 text-center shadow-soft">
            <p className="text-xl font-bold text-ink">Suelta aquí el Excel o los PDFs</p>
            <p className="mt-2 text-sm text-slate-600">CheckIA validará hojas, SIN/DOC, texto extraído y coherencia documental.</p>
          </div>
        </div>
      )}
      <CsvValidationModal modal={modal} onClose={() => setModal(null)} />
    </div>
  )
}
