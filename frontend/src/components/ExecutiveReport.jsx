import { Copy, Download } from 'lucide-react'

export default function ExecutiveReport({ report }) {
  if (!report) return null
  const text = [
    report.summary,
    `Total de casos: ${report.total_cases}`,
    `Casos criticos: ${report.critical_cases}`,
    'Senales principales:',
    ...(report.main_signals || []).map((item) => `- ${item.signal}: ${item.count}`),
    'Recomendaciones:',
    ...(report.recommendations || []).map((item) => `- ${item}`),
    'Limitaciones:',
    ...(report.limitations || []).map((item) => `- ${item}`)
  ].join('\n')

  function downloadJson() {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'checkia-reporte.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-xl font-bold text-ink">Resumen ejecutivo</h3>
        <div className="flex gap-2">
          <button onClick={() => navigator.clipboard.writeText(text)} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold hover:bg-slate-50"><Copy size={16} /> Copiar</button>
          <button onClick={downloadJson} className="inline-flex items-center gap-2 rounded-lg bg-electric px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"><Download size={16} /> JSON</button>
        </div>
      </div>
      <p className="mt-4 leading-7 text-slate-700">{report.summary}</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Block title="Señales principales" items={(report.main_signals || []).map((item) => `${item.signal}: ${item.count}`)} />
        <Block title="Recomendaciones" items={report.recommendations || []} />
        <Block title="Proveedores con más alertas" items={(report.providers || []).map((p) => `${p.provider_name}: ${p.alerts} alertas`)} />
        <Block title="Limitaciones" items={report.limitations || []} />
      </div>
    </div>
  )
}

function Block({ title, items }) {
  return <div className="rounded-lg bg-slate-50 p-4"><h4 className="font-bold text-ink">{title}</h4><ul className="mt-3 space-y-2 text-sm text-slate-700">{items.map((item) => <li key={item}>{item}</li>)}</ul></div>
}
