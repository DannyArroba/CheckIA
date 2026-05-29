import { useEffect, useState } from 'react'
import { Database, FileSpreadsheet, Files, RefreshCw, ScanSearch, Trash2 } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import KpiCard from '../components/KpiCard.jsx'
import CsvValidationModal from '../components/CsvValidationModal.jsx'

export default function DataLab() {
  const [dbStatus, setDbStatus] = useState(null)
  const [hackia, setHackia] = useState(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [modal, setModal] = useState(null)

  async function refresh() {
    const [db, hackiaSummary] = await Promise.all([
      claimsApi.databaseStatus().catch((error) => ({ connected: false, error: error.message })),
      claimsApi.hackiaSummary().catch(() => null)
    ])
    setDbStatus(db)
    setHackia(hackiaSummary)
  }

  useEffect(() => {
    refresh()
  }, [])

  async function uploadHackiaExcel(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    await importExcel(file)
  }

  async function uploadHackiaPdfs(event) {
    const files = event.target.files
    event.target.value = ''
    if (!files?.length) return
    await importPdfs(files)
  }

  async function importExcel(file) {
    setBusy(true)
    setMessage('Importando Excel multi-hoja del HackIAthon...')
    try {
      const result = await claimsApi.uploadHackiaExcel(file)
      setMessage('')
      setModal({
        type: 'success',
        title: 'Excel HackIAthon importado',
        body: `Se leyeron las hojas ${result.sheets.join(', ')} y se recalculó el análisis de riesgo.`,
        stats: [
          { label: 'Siniestros', value: result.records.siniestros },
          { label: 'Documentos', value: result.records.documentos },
          { label: 'Alertas', value: result.analysis.alertas_generadas }
        ]
      })
      await refresh()
    } catch (error) {
      setMessage('')
      setModal({ title: 'No se pudo importar el Excel', body: String(error.detail || error.message), type: 'error' })
    } finally {
      setBusy(false)
    }
  }

  async function importPdfs(files) {
    setBusy(true)
    setMessage(`Procesando ${files.length} PDF(s). Esto puede tardar si algún archivo requiere OCR...`)
    try {
      const result = await claimsApi.uploadHackiaPdfs(files)
      const rejected = result.details?.filter((item) => item.rechazado).length || 0
      setMessage('')
      setModal({
        type: rejected ? 'warning' : 'success',
        title: rejected ? 'PDFs procesados con alertas' : 'PDFs procesados',
        body: rejected
          ? `${rejected} archivo(s) no tenían SIN-xxxx ni DOC-xxxx y fueron omitidos por no corresponder al expediente.`
          : 'CheckIA extrajo texto, detectó SIN/DOC y recalculó alertas.',
        stats: [
          { label: 'Procesados', value: result.stats.pdfs_procesados },
          { label: 'OCR usado', value: result.stats.ocr_usado },
          { label: 'Sin relación', value: result.stats.sin_relacion }
        ]
      })
      await refresh()
    } catch (error) {
      setMessage('')
      setModal({ title: 'No se pudieron procesar los PDFs', body: String(error.detail || error.message), type: 'error' })
    } finally {
      setBusy(false)
    }
  }

  async function recalculateHackia() {
    setBusy(true)
    setMessage('Recalculando alertas y score HackIAthon...')
    try {
      const result = await claimsApi.hackiaRecalculate()
      setMessage(`Análisis recalculado: ${result.siniestros} siniestros y ${result.alertas_generadas} alertas.`)
      await refresh()
    } catch (error) {
      setModal({ title: 'No se pudo recalcular', body: String(error.detail || error.message), type: 'error' })
    } finally {
      setBusy(false)
    }
  }

  async function clearHackia() {
    if (!window.confirm('¿Seguro que quieres borrar el dataset HackIAthon cargado?')) return
    setBusy(true)
    setMessage('Borrando dataset HackIAthon actual...')
    try {
      const result = await claimsApi.hackiaClear()
      setMessage(result.message)
      await refresh()
    } catch (error) {
      setModal({ title: 'No se pudo limpiar el dataset', body: String(error.detail || error.message), type: 'error' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <KpiCard title="Siniestros Excel" value={hackia?.counts?.siniestros ?? 0} helper="Hoja 1_Siniestros" icon={Database} />
        <KpiCard title="Documentos Excel" value={hackia?.counts?.documentos ?? 0} helper="Hoja 5_Documentos" tone="slate" />
        <KpiCard title="PDFs procesados" value={hackia?.counts?.documentos_extraidos ?? 0} helper="Texto/OCR extraído" tone="yellow" />
        <KpiCard title="Alertas generadas" value={hackia?.counts?.alertas_fraude ?? 0} helper="Score recalculado" tone="red" />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-xl font-bold text-ink">Base de datos MySQL</h3>
            <p className="mt-1 text-sm text-slate-600">
              {dbStatus?.connected ? `Conectada a ${dbStatus.database} en ${dbStatus.host}:${dbStatus.port}` : 'Sin conexión confirmada a MySQL/XAMPP.'}
            </p>
          </div>
          <button onClick={refresh} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold hover:bg-slate-50">
            <RefreshCw size={16} /> Revisar
          </button>
        </div>
        {dbStatus?.error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">{dbStatus.error}</p>}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-ink">Importación HackIAthon: Excel + PDFs</h3>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              También puedes arrastrar el Excel o los PDFs sobre cualquier pantalla de la aplicación. CheckIA validará estructura, SIN/DOC y coherencia básica.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button disabled={busy} onClick={recalculateHackia} className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-slate-200 px-4 font-semibold hover:bg-slate-50 disabled:opacity-60">
              <ScanSearch size={18} /> Recalcular
            </button>
            <button disabled={busy} onClick={clearHackia} className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-red-200 px-4 font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60">
              <Trash2 size={18} /> Borrar dataset
            </button>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <label className="flex min-h-20 cursor-pointer items-center gap-3 rounded-lg border border-dashed border-blue-200 bg-blue-50 px-4 text-blue-950 hover:border-electric">
            <FileSpreadsheet size={24} className="text-electric" />
            <span>
              <strong className="block">Subir Excel completo</strong>
              <span className="text-sm">Acepta README + 1_Siniestros a 5_Documentos.</span>
            </span>
            <input type="file" accept=".xlsx,.xls,.xlsm" className="hidden" onChange={uploadHackiaExcel} />
          </label>
          <label className="flex min-h-20 cursor-pointer items-center gap-3 rounded-lg border border-dashed border-amber-200 bg-amber-50 px-4 text-amber-950 hover:border-amber-400">
            <Files size={24} className="text-amber-600" />
            <span>
              <strong className="block">Subir lote de PDFs</strong>
              <span className="text-sm">Acepta selección múltiple de facturas, DA y PP.</span>
            </span>
            <input type="file" accept=".pdf" multiple className="hidden" onChange={uploadHackiaPdfs} />
          </label>
        </div>
        {!!hackia?.logs?.length && (
          <div className="mt-5 rounded-lg bg-slate-50 p-4">
            <p className="text-sm font-bold text-ink">Últimos procesos</p>
            <div className="mt-3 space-y-2">
              {hackia.logs.slice(0, 4).map((log, index) => (
                <p key={`${log.tipo}-${index}`} className="text-sm text-slate-600">
                  <strong>{log.tipo}:</strong> {log.mensaje}
                </p>
              ))}
            </div>
          </div>
        )}
      </section>

      {message && <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm font-semibold text-blue-950">{message}</div>}
      <CsvValidationModal modal={modal} onClose={() => setModal(null)} />
    </div>
  )
}
