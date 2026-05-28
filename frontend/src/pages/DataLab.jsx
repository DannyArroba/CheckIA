import { useEffect, useState } from 'react'
import { Database, FilePlus2, RefreshCw, UploadCloud } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import KpiCard from '../components/KpiCard.jsx'
import CsvValidationModal, { buildUploadErrorModal, buildUploadSuccessModal } from '../components/CsvValidationModal.jsx'

export default function DataLab() {
  const [dbStatus, setDbStatus] = useState(null)
  const [summary, setSummary] = useState(null)
  const [count, setCount] = useState(25)
  const [riskMix, setRiskMix] = useState('balanceado')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [modal, setModal] = useState(null)

  async function refresh() {
    const [db, dashboard] = await Promise.all([
      claimsApi.databaseStatus().catch((error) => ({ connected: false, error: error.message })),
      claimsApi.summary()
    ])
    setDbStatus(db)
    setSummary(dashboard)
  }

  useEffect(() => {
    refresh()
  }, [])

  async function syncDb() {
    setBusy(true)
    setMessage('Sincronizando datos, resultados IA y reglas con MySQL...')
    try {
      const result = await claimsApi.syncDatabase()
      setMessage(`Sincronización lista: ${result.source.claims} siniestros y ${result.risk.risk_results} scores guardados.`)
      await refresh()
    } catch {
      setModal({
        title: 'No se pudo sincronizar MySQL',
        body: 'Revisa que XAMPP/MySQL esté activo y que exista la base checkia.',
        type: 'error'
      })
    } finally {
      setBusy(false)
    }
  }

  async function generate() {
    setBusy(true)
    setMessage('Generando CSV descargable...')
    try {
      const result = await claimsApi.generateDataset(Number(count), riskMix)
      const link = document.createElement('a')
      link.href = result.download_url
      link.download = result.csv_file
      link.click()
      setMessage(`CSV creado con ${result.created} siniestros. Descárgalo y luego cárgalo manualmente desde tus archivos para actualizar el análisis.`)
    } catch {
      setModal({
        title: 'No se pudo generar el CSV',
        body: 'Intenta nuevamente con una cantidad entre 1 y 100 siniestros.',
        type: 'error'
      })
    } finally {
      setBusy(false)
    }
  }

  async function upload(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setBusy(true)
    setMessage('Validando estructura del CSV...')
    try {
      const result = await claimsApi.upload(file)
      setMessage('')
      setModal(buildUploadSuccessModal(result))
      await refresh()
    } catch (error) {
      setMessage('')
      setModal(buildUploadErrorModal(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <KpiCard title="Total siniestros" value={summary?.total_claims ?? '-'} helper="MySQL activo + modelo recalculado" icon={Database} />
        <KpiCard title="Verdes" value={summary?.green_cases ?? '-'} helper="Riesgo bajo" tone="green" />
        <KpiCard title="Amarillos" value={summary?.yellow_cases ?? '-'} helper="Revisión recomendada" tone="yellow" />
        <KpiCard title="Rojos" value={summary?.red_cases ?? '-'} helper="Caso prioritario" tone="red" />
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
        <button disabled={busy} onClick={syncDb} className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-lg bg-electric px-4 font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
          <Database size={18} /> Sincronizar datos y resultados IA
        </button>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-xl font-bold text-ink">Generador de siniestros sintéticos</h3>
        <p className="mt-1 text-sm text-slate-600">Crea un CSV descargable separado por punto y coma para abrirlo bien en Excel. No modifica el sistema hasta que tú lo cargues manualmente.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-[160px_190px_auto]">
          <input type="number" min="1" max="100" value={count} onChange={(event) => setCount(event.target.value)} className="min-h-11 rounded-lg border border-slate-200 px-3" />
          <select value={riskMix} onChange={(event) => setRiskMix(event.target.value)} className="min-h-11 rounded-lg border border-slate-200 px-3">
            <option value="balanceado">Balanceado</option>
            <option value="alto">Más casos críticos</option>
          </select>
          <button disabled={busy} onClick={generate} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-ink px-4 font-semibold text-white hover:bg-slate-800 disabled:opacity-60">
            <FilePlus2 size={18} /> Crear CSV descargable
          </button>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-xl font-bold text-ink">Cargar CSV de siniestros</h3>
        <p className="mt-1 text-sm text-slate-600">
          Acepta CSV separado por punto y coma o coma. Si vuelves a cargar un archivo ya usado, CheckIA solo agrega los claim_id nuevos y omite duplicados.
        </p>
        <label className="mt-4 inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-4 font-semibold hover:bg-slate-50">
          <UploadCloud size={18} /> Seleccionar CSV desde mi PC
          <input type="file" accept=".csv" className="hidden" onChange={upload} />
        </label>
      </section>

      {message && <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm font-semibold text-blue-950">{message}</div>}
      <CsvValidationModal modal={modal} onClose={() => setModal(null)} />
    </div>
  )
}
