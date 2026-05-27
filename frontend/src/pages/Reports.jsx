import { useEffect, useState } from 'react'
import { claimsApi } from '../api/claimsApi.js'
import ExecutiveReport from '../components/ExecutiveReport.jsx'

export default function Reports() {
  const [report, setReport] = useState(null)

  useEffect(() => {
    claimsApi.report().then(setReport).catch(() => setReport(null))
  }, [])

  return report ? <ExecutiveReport report={report} /> : <div className="rounded-lg bg-white p-8 shadow-soft">Cargando reporte...</div>
}
