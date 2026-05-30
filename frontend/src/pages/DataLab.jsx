import { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  FileSpreadsheet,
  Files,
  LoaderCircle,
  RefreshCw,
  ScanSearch,
  Server,
  Trash2,
  XCircle
} from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import KpiCard from '../components/KpiCard.jsx'
import CsvValidationModal from '../components/CsvValidationModal.jsx'

export default function DataLab() {
  const [dbStatus, setDbStatus] = useState(null)
  const [hackia, setHackia] = useState(null)
  const [system, setSystem] = useState(null)
  const [message, setMessage] = useState('')
  const [processLog, setProcessLog] = useState([])
  const [busy, setBusy] = useState(false)
  const [modal, setModal] = useState(null)

  async function refresh() {
    const [db, hackiaSummary, systemStatus] = await Promise.all([
      claimsApi.databaseStatus().catch((error) => ({ connected: false, error: error.message })),
      claimsApi.hackiaSummary().catch(() => null),
      claimsApi.systemStatus().catch((error) => ({ error: error.message }))
    ])
    setDbStatus(db)
    setHackia(hackiaSummary)
    setSystem(systemStatus)
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
    startProcess('Importación de Excel', [
      `Archivo seleccionado: ${file.name}`,
      'Subiendo archivo al backend FastAPI.',
      'Validando hojas requeridas: 1_Siniestros a 5_Documentos.',
      'Guardando registros en MySQL.',
      'Recalculando score y alertas.'
    ])
    try {
      const result = await claimsApi.uploadHackiaExcel(file)
      finishProcess('Excel importado correctamente.')
      setModal({
        type: 'success',
        title: 'Excel importado',
        body: `Se leyeron las hojas ${result.sheets.join(', ')} y se recalculó el análisis de riesgo.`,
        stats: [
          { label: 'Siniestros', value: result.records.siniestros },
          { label: 'Documentos', value: result.records.documentos },
          { label: 'Alertas', value: result.analysis.alertas_generadas }
        ]
      })
      await refresh()
    } catch (error) {
      failProcess(error)
      setModal({ title: 'No se pudo importar el Excel', body: String(error.detail || error.message), type: 'error' })
    } finally {
      setBusy(false)
    }
  }

  async function importPdfs(files) {
    setBusy(true)
    startProcess('Procesamiento de PDFs', [
      `Archivos seleccionados: ${files.length}`,
      'Subiendo PDFs al backend FastAPI.',
      'Extrayendo texto con parser PDF.',
      'Aplicando OCR cuando el texto no sea legible.',
      'Vinculando SIN/DOC, guardando resultados y recalculando alertas.'
    ])
    try {
      const result = await claimsApi.uploadHackiaPdfs(files)
      const rejected = result.details?.filter((item) => item.rechazado).length || 0
      finishProcess(`PDFs aceptados: ${result.stats.pdfs_procesados}. Rechazados: ${rejected}.`)
      setModal({
        type: rejected ? 'warning' : 'success',
        title: rejected ? 'PDFs procesados con alertas' : 'PDFs procesados',
        body: rejected
          ? `${rejected} archivo(s) fueron rechazados porque no coinciden con los SIN/DOC esperados en el Excel cargado.`
          : 'CheckIA validó que los PDFs pertenecen al Excel, extrajo texto y recalculó alertas.',
        stats: [
          { label: 'Aceptados', value: result.stats.pdfs_procesados },
          { label: 'Rechazados', value: result.stats.rechazados ?? rejected },
          { label: 'OCR usado', value: result.stats.ocr_usado },
          { label: 'Vinculados', value: result.stats.vinculados }
        ]
      })
      await refresh()
    } catch (error) {
      failProcess(error)
      setModal({ title: 'No se pudieron procesar los PDFs', body: String(error.detail || error.message), type: 'error' })
    } finally {
      setBusy(false)
    }
  }

  async function recalculateHackia() {
    setBusy(true)
    startProcess('Recálculo de análisis', [
      'Leyendo siniestros, pólizas, asegurados, proveedores y documentos.',
      'Evaluando reglas explicables.',
      'Actualizando alertas_fraude y analisis_fraude en MySQL.'
    ])
    try {
      const result = await claimsApi.hackiaRecalculate()
      finishProcess(`Análisis recalculado: ${result.siniestros} siniestros y ${result.alertas_generadas} alertas.`)
      await refresh()
    } catch (error) {
      failProcess(error)
      setModal({ title: 'No se pudo recalcular', body: String(error.detail || error.message), type: 'error' })
    } finally {
      setBusy(false)
    }
  }

  async function clearHackia() {
    if (!window.confirm('¿Seguro que quieres borrar el dataset cargado?')) return
    setBusy(true)
    startProcess('Limpieza de dataset', [
      'Eliminando siniestros, documentos, PDFs extraídos, alertas y análisis.',
      'Actualizando indicadores de la pantalla.'
    ])
    try {
      const result = await claimsApi.hackiaClear()
      finishProcess(result.message)
      await refresh()
    } catch (error) {
      failProcess(error)
      setModal({ title: 'No se pudo limpiar el dataset', body: String(error.detail || error.message), type: 'error' })
    } finally {
      setBusy(false)
    }
  }

  function startProcess(title, steps) {
    setMessage(title)
    setProcessLog([
      { tone: 'active', text: title },
      ...steps.map((text) => ({ tone: 'pending', text }))
    ])
  }

  function finishProcess(text) {
    setMessage(text)
    setProcessLog((items) => [
      ...items.map((item) => ({ ...item, tone: item.tone === 'active' || item.tone === 'pending' ? 'done' : item.tone })),
      { tone: 'done', text }
    ])
  }

  function failProcess(error) {
    const detail = String(error.detail || error.message || 'Error desconocido')
    setMessage(`Error: ${detail}`)
    setProcessLog((items) => [
      ...items.map((item) => ({ ...item, tone: item.tone === 'active' ? 'error' : item.tone })),
      { tone: 'error', text: detail }
    ])
  }

  const hasExcelClaims = Number(hackia?.counts?.siniestros || 0) > 0

  return (
    <div className="space-y-6">
      <SystemStatus system={system} dbStatus={dbStatus} />

      <div className="grid gap-4 md:grid-cols-4">
        <KpiCard title="Siniestros Excel" value={hackia?.counts?.siniestros ?? 0} helper="Hoja 1_Siniestros" icon={Database} />
        <KpiCard title="Documentos Excel" value={hackia?.counts?.documentos ?? 0} helper="Hoja 5_Documentos" tone="slate" />
        <KpiCard title="PDFs procesados" value={hackia?.counts?.documentos_extraidos ?? 0} helper="Texto/OCR extraído" tone="yellow" />
        <KpiCard title="Alertas generadas" value={hackia?.counts?.alertas_fraude ?? 0} helper="Score recalculado" tone="red" />
      </div>

      <ProcessPanel message={message} steps={processLog} busy={busy} />

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
            <h3 className="text-xl font-bold text-ink">Importación de datos: Excel + PDFs</h3>
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
          <label className={`flex min-h-20 items-center gap-3 rounded-lg border border-dashed px-4 ${hasExcelClaims ? 'cursor-pointer border-amber-200 bg-amber-50 text-amber-950 hover:border-amber-400' : 'cursor-not-allowed border-slate-200 bg-slate-50 text-slate-500'}`}>
            <Files size={24} className="text-amber-600" />
            <span>
              <strong className="block">Subir lote de PDFs</strong>
              <span className="text-sm">{hasExcelClaims ? 'Acepta selección múltiple de facturas, DA y PP.' : 'Primero sube el Excel para vincular SIN/DOC.'}</span>
            </span>
            <input type="file" accept=".pdf" multiple disabled={!hasExcelClaims} className="hidden" onChange={uploadHackiaPdfs} />
          </label>
        </div>
        {!!hackia?.logs?.length && (
          <div className="mt-5 rounded-lg bg-slate-50 p-4">
            <p className="text-sm font-bold text-ink">Últimos procesos</p>
            <div className="mt-3 space-y-2">
              {hackia.logs.slice(0, 4).map((log, index) => (
                <p key={`${log.tipo}-${index}`} className="text-sm text-slate-600">
                  <strong>{cleanUiText(log.tipo)}:</strong> {cleanUiText(log.mensaje)}
                </p>
              ))}
            </div>
          </div>
        )}
      </section>

      <CsvValidationModal modal={modal} onClose={() => setModal(null)} />
    </div>
  )
}

function SystemStatus({ system, dbStatus }) {
  const ollamaReady = Boolean(system?.ollama?.available && system?.ollama?.model_found)
  const ollamaDetail = system?.ollama?.available
    ? `${system.ollama.model} listo${system.ollama.using_fallback ? ` (respaldo de ${system.ollama.configured_model})` : ''}`
    : 'Agente IA sin conexión activa'
  const ocrReady = Boolean(system?.ocr?.ready)
  const popplerReady = Boolean(system?.ocr?.poppler?.ok)
  const ocrDetail = ocrReady
    ? 'Tesseract + Poppler listos'
    : popplerReady
      ? 'Poppler listo; falta Tesseract para OCR de PDFs escaneados'
      : 'Falta Poppler o Tesseract para PDFs escaneados'
  const cards = [
    {
      title: 'Frontend',
      detail: 'Vite/React activo en navegador',
      ok: true,
      icon: Activity
    },
    {
      title: 'Backend',
      detail: system?.api?.ok ? `FastAPI + Python ${system.api.python}` : 'Sin respuesta del API',
      ok: Boolean(system?.api?.ok),
      icon: Server
    },
    {
      title: 'Node',
      detail: system?.node?.ok ? `Node ${system.node.version}` : 'Node no detectado desde el backend',
      ok: Boolean(system?.node?.ok),
      icon: Cpu
    },
    {
      title: 'MySQL',
      detail: dbStatus?.connected ? `${dbStatus.database} en ${dbStatus.host}:${dbStatus.port}` : dbStatus?.error || 'Sin conexión',
      ok: Boolean(dbStatus?.connected),
      icon: Database
    },
    {
      title: 'Ollama',
      detail: ollamaDetail,
      ok: ollamaReady,
      tone: ollamaReady ? 'ok' : 'error',
      icon: Cpu
    },
    {
      title: 'OCR PDF',
      detail: ocrDetail,
      ok: ocrReady,
      tone: ocrReady ? 'ok' : popplerReady ? 'warning' : 'error',
      icon: Files
    }
  ]

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-bold text-ink">Estado del sistema</h3>
          <p className="mt-1 text-sm text-slate-600">Servicios necesarios para cargar, procesar y consultar datos.</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-6">
        {cards.map((card) => <StatusCard key={card.title} {...card} />)}
      </div>
    </section>
  )
}

function StatusCard({ title, detail, ok, tone, icon: Icon }) {
  const state = tone || (ok ? 'ok' : 'error')
  const styles = {
    ok: {
      box: 'border-emerald-100 bg-emerald-50',
      icon: 'text-emerald-700',
      title: 'text-emerald-950',
      text: 'text-emerald-800',
      badge: <CheckCircle2 size={18} className="text-emerald-700" />
    },
    warning: {
      box: 'border-amber-100 bg-amber-50',
      icon: 'text-amber-700',
      title: 'text-amber-950',
      text: 'text-amber-800',
      badge: <AlertTriangle size={18} className="text-amber-700" />
    },
    error: {
      box: 'border-red-100 bg-red-50',
      icon: 'text-red-700',
      title: 'text-red-950',
      text: 'text-red-800',
      badge: <XCircle size={18} className="text-red-700" />
    }
  }[state]
  return (
    <div className={`rounded-lg border p-4 ${styles.box}`}>
      <div className="flex items-center justify-between gap-3">
        <Icon size={20} className={styles.icon} />
        {styles.badge}
      </div>
      <p className={`mt-3 text-sm font-bold ${styles.title}`}>{title}</p>
      <p className={`mt-1 text-xs leading-5 ${styles.text}`}>{detail}</p>
    </div>
  )
}

function cleanUiText(value) {
  if (value === null || value === undefined) return ''
  let text = String(value)
  const replacements = {
    analisis: 'análisis',
    Analisis: 'Análisis',
    importacion: 'importación',
    Importacion: 'Importación',
    recalculo: 'recálculo',
    Recalculo: 'Recálculo',
    'AnÃ¡lisis': 'Análisis',
    'anÃ¡lisis': 'análisis',
    'ImportaciÃ³n': 'Importación',
    'importaciÃ³n': 'importación',
    'recalculÃ³': 'recalculó',
    'extraÃ­do': 'extraído',
    'pÃ³lizas': 'pólizas',
    'Ã¡': 'á',
    'Ã©': 'é',
    'Ã­': 'í',
    'Ã³': 'ó',
    'Ãº': 'ú',
    'Ã±': 'ñ',
    'Â¿': '¿',
    'Â¡': '¡'
  }
  Object.entries(replacements).forEach(([bad, good]) => {
    text = text.replaceAll(bad, good)
  })
  return text
}

function ProcessPanel({ message, steps, busy }) {
  if (!message && !steps.length) return null
  return (
    <section className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-950">
      <div className="flex items-center gap-2 font-bold">
        {busy && <LoaderCircle size={17} className="animate-spin" />}
        {message}
      </div>
      {!!steps.length && (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {steps.map((step, index) => <ProcessStep key={`${step.text}-${index}`} step={step} />)}
        </div>
      )}
    </section>
  )
}

function ProcessStep({ step }) {
  const tone = step.tone || 'pending'
  const styles = {
    active: 'border-blue-200 bg-white text-blue-900',
    pending: 'border-slate-200 bg-white/70 text-slate-600',
    done: 'border-emerald-200 bg-white text-emerald-800',
    error: 'border-red-200 bg-white text-red-800'
  }
  return (
    <div className={`flex items-start gap-2 rounded-lg border px-3 py-2 ${styles[tone] || styles.pending}`}>
      {tone === 'done' ? (
        <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
      ) : tone === 'error' ? (
        <XCircle size={16} className="mt-0.5 shrink-0" />
      ) : (
        <LoaderCircle size={16} className={`mt-0.5 shrink-0 ${tone === 'active' ? 'animate-spin' : ''}`} />
      )}
      <span>{step.text}</span>
    </div>
  )
}
