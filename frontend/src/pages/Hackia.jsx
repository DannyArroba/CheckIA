import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ArrowDown, ArrowUp, ArrowUpDown, Download, FileText, Search } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'

const tabs = [
  { id: 'siniestros', label: 'Siniestros' },
  { id: 'polizas', label: 'Polizas' },
  { id: 'asegurados', label: 'Asegurados' },
  { id: 'proveedores', label: 'Proveedores' },
  { id: 'documentos', label: 'Documentos' },
  { id: 'pdfs', label: 'PDFs subidos' },
  { id: 'analisis', label: 'Analisis' }
]

const riskTones = {
  Bajo: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Medio: 'bg-amber-50 text-amber-700 border-amber-200',
  Alto: 'bg-red-50 text-red-700 border-red-200',
  Critico: 'bg-rose-100 text-rose-800 border-rose-200'
}

export default function Hackia() {
  const [claims, setClaims] = useState([])
  const [tables, setTables] = useState({})
  const [pdfs, setPdfs] = useState([])
  const [selected, setSelected] = useState(null)
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState('siniestros')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([claimsApi.hackiaClaims(), claimsApi.hackiaTables(), claimsApi.hackiaPdfs()])
      .then(([claimsData, tablesData, pdfRows]) => {
        setClaims(claimsData)
        setTables(tablesData)
        setPdfs(pdfRows)
      })
      .catch((err) => setError(String(err.detail || err.message)))
  }, [])

  const rows = tab === 'siniestros' ? claims : tab === 'pdfs' ? pdfs : (tables[tab] || [])
  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    return rows.filter((row) => Object.values(row).join(' ').toLowerCase().includes(q))
  }, [rows, query])

  async function openClaim(id) {
    const detail = await claimsApi.hackiaClaim(id)
    setSelected(detail)
  }

  if (error) return <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-red-800">{error}</div>

  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-xl font-bold text-ink">Tablas de informacion</h3>
            <p className="mt-1 text-sm text-slate-600">Informacion importada desde Excel y PDFs procesados, con vinculos por SIN/DOC.</p>
          </div>
          <label className="flex min-h-11 min-w-80 items-center gap-2 rounded-lg border border-slate-200 px-3">
            <Search size={18} className="text-slate-400" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="w-full outline-none" placeholder="Buscar en la tabla actual" />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {tabs.map((item) => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              className={`rounded-lg px-3 py-2 text-sm font-bold ${tab === item.id ? 'bg-ink text-white' : 'border border-slate-200 text-slate-600 hover:bg-slate-50'}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      {tab === 'siniestros' ? (
        <ClaimsTable rows={filtered} onOpen={openClaim} />
      ) : tab === 'pdfs' ? (
        <PdfsTable rows={filtered} onOpen={openClaim} />
      ) : (
        <GenericTable rows={filtered} />
      )}

      {selected && <HackiaDetail detail={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function ClaimsTable({ rows, onOpen }) {
  const [sort, setSort] = useState({ key: 'puntaje_riesgo', direction: 'desc' })
  const columns = [
    ['ID Siniestro', 'id_siniestro'],
    ['ID Poliza', 'id_poliza'],
    ['ID Asegurado', 'id_asegurado'],
    ['Ramo', 'ramo'],
    ['Placa Vehiculo Asegurado', 'placa'],
    ['Cobertura', 'cobertura'],
    ['Fecha Ocurrencia', 'fecha_siniestro'],
    ['Fecha Reporte', 'fecha_reporte'],
    ['Dias Ocurr-Reporte', 'dias_ocurrencia_reporte'],
    ['Monto Reclamado ($)', 'monto_reclamado', 'money'],
    ['Monto Estimado ($)', 'monto_estimado', 'money'],
    ['Monto Pagado ($)', 'monto_pagado', 'money'],
    ['Estado', 'estado'],
    ['Sucursal', 'sucursal'],
    ['ID Proveedor', 'id_proveedor'],
    ['Proveedor', 'nombre_proveedor'],
    ['Descripcion del Evento', 'descripcion_evento', 'long'],
    ['Docs Completos', 'docs_completos', 'bool'],
    ['Prov. Lista Restrictiva', 'proveedor_lista_restrictiva', 'bool'],
    ['Dias desde Inicio Poliza', 'dias_desde_inicio_poliza'],
    ['Dias hasta Fin Poliza', 'dias_hasta_fin_poliza'],
    ['N Reclamos Previos', 'reclamos_previos'],
    ['Suma Asegurada ($)', 'suma_asegurada', 'money'],
    ['Similitud Narrativa Max.', 'similitud_narrativa_max'],
    ['Numero Parte Policial', 'numero_parte_policial'],
    ['Score', 'puntaje_riesgo', 'score'],
    ['Nivel', 'nivel_riesgo', 'risk'],
    ['Documentos', 'documentos'],
    ['PDFs', 'pdfs_procesados'],
    ['Alertas', 'alertas']
  ]
  const sortedRows = useMemo(() => {
    return [...rows].sort((a, b) => compareTableValues(sortValue(a, sort.key), sortValue(b, sort.key), sort.direction))
  }, [rows, sort])

  function toggleSort(key) {
    setSort((current) => {
      if (current.key !== key) return { key, direction: 'asc' }
      return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
    })
  }

  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-soft">
      <div className="overflow-x-auto">
        <table className="min-w-[2800px] divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {columns.map(([label, key]) => (
                <th key={label} className="px-4 py-3 text-left text-xs font-bold uppercase text-slate-500">
                  <button type="button" onClick={() => toggleSort(key)} className="inline-flex items-center gap-1 hover:text-electric" title={`Ordenar por ${label}`}>
                    <span>{label}</span>
                    {sort.key === key
                      ? sort.direction === 'asc'
                        ? <ArrowUp size={13} />
                        : <ArrowDown size={13} />
                      : <ArrowUpDown size={13} className="text-slate-300" />}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sortedRows.map((claim) => (
              <tr key={claim.id_siniestro} onClick={() => onOpen(claim.id_siniestro)} className="cursor-pointer hover:bg-blue-50/50">
                {columns.map(([label, key, type]) => (
                  <td key={`${claim.id_siniestro}-${key}`} className={`px-4 py-3 text-sm ${type === 'long' ? 'min-w-80 text-slate-600' : 'whitespace-nowrap'}`}>
                    {renderClaimCell(claim, key, type)}
                  </td>
                ))}
              </tr>
            ))}
            {!sortedRows.length && <EmptyRow colSpan={columns.length} />}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function sortValue(row, key) {
  const value = row[key]
  if (value === null || value === undefined || value === '-') return ''
  if (typeof value === 'number') return value
  if (['monto_reclamado', 'monto_estimado', 'monto_pagado', 'dias_ocurrencia_reporte', 'dias_desde_inicio_poliza', 'dias_hasta_fin_poliza', 'reclamos_previos', 'suma_asegurada', 'similitud_narrativa_max', 'puntaje_riesgo', 'documentos', 'pdfs_procesados', 'alertas'].includes(key)) {
    const number = Number(String(value).replace(/[^0-9.-]/g, ''))
    return Number.isNaN(number) ? 0 : number
  }
  return String(value).toLowerCase()
}

function compareTableValues(a, b, direction) {
  if (typeof a === 'number' && typeof b === 'number') {
    return direction === 'asc' ? a - b : b - a
  }
  const result = String(a).localeCompare(String(b), 'es', { numeric: true, sensitivity: 'base' })
  return direction === 'asc' ? result : -result
}

function renderClaimCell(claim, key, type) {
  if (key === 'id_siniestro') return <span className="font-bold text-electric">{claim[key]}</span>
  if (type === 'money') return `$${Number(claim[key] || 0).toLocaleString()}`
  if (type === 'bool') return claim[key] ? 'Si' : 'No'
  if (type === 'score') return <span className="font-bold text-ink">{claim[key] ?? 0}</span>
  if (type === 'risk') {
    return <span className={`rounded-full border px-3 py-1 text-xs font-bold ${riskTones[claim[key]] || riskTones.Bajo}`}>{claim[key] || 'Bajo'}</span>
  }
  return claim[key] ?? '-'
}

function PdfsTable({ rows, onOpen }) {
  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-soft">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {['PDF', 'Siniestro', 'Documento', 'Tipo', 'Extraccion', 'OCR', 'Texto', 'Acciones'].map((label) => (
                <th key={label} className="px-4 py-3 text-left text-xs font-bold uppercase text-slate-500">{label}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((pdf) => (
              <tr key={`${pdf.id_documento}-${pdf.nombre_archivo_pdf}`} className="hover:bg-slate-50">
                <td className="max-w-80 truncate px-4 py-3 text-sm font-semibold text-ink" title={pdf.nombre_archivo_pdf}>{pdf.nombre_archivo_pdf || '-'}</td>
                <td className="px-4 py-3 text-sm">
                  <button onClick={() => onOpen(pdf.id_siniestro)} className="font-bold text-electric hover:underline">{pdf.id_siniestro || '-'}</button>
                </td>
                <td className="px-4 py-3 text-sm">{pdf.id_documento}</td>
                <td className="px-4 py-3 text-sm">{pdf.tipo_documento || '-'}</td>
                <td className="px-4 py-3 text-sm">{pdf.metodo_extraccion || 'pendiente'}</td>
                <td className="px-4 py-3 text-sm">{pdf.ocr_usado ? 'Si' : 'No'}</td>
                <td className="px-4 py-3 text-sm">{Number(pdf.caracteres_extraidos || 0).toLocaleString()} caracteres</td>
                <td className="px-4 py-3 text-sm">
                  <a
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 font-bold text-slate-700 hover:bg-slate-50"
                    href={claimsApi.hackiaPdfDownloadUrl(pdf.id_documento)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Download size={15} /> Descargar
                  </a>
                </td>
              </tr>
            ))}
            {!rows.length && <EmptyRow colSpan={8} />}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function GenericTable({ rows }) {
  const columns = rows.length ? Object.keys(rows[0]) : []
  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-soft">
      <div className="overflow-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => <th key={column} className="whitespace-nowrap px-4 py-3 text-left text-xs font-bold uppercase text-slate-500">{column.replaceAll('_', ' ')}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, index) => (
              <tr key={index} className="hover:bg-slate-50">
                {columns.map((column) => (
                  <td key={column} className="max-w-80 truncate px-4 py-3 text-sm text-slate-700" title={String(row[column] ?? '')}>{String(row[column] ?? '-')}</td>
                ))}
              </tr>
            ))}
            {!rows.length && <EmptyRow colSpan={Math.max(columns.length, 1)} />}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function EmptyRow({ colSpan }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-8 text-center text-sm text-slate-500">
        No hay datos cargados en esta seccion. Importa el Excel desde Datos.
      </td>
    </tr>
  )
}

export function HackiaDetail({ detail, onClose }) {
  const { siniestro, poliza, asegurado, proveedor, documentos, extraidos, alertas, analisis, facturas, partes_policiales, declaraciones } = detail
  return (
    <div className="fixed inset-0 z-40 bg-ink/30 p-4 backdrop-blur-sm" onClick={onClose}>
      <aside className="ml-auto h-full max-w-4xl overflow-y-auto rounded-lg bg-white p-6 shadow-soft" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-electric">{siniestro.id_siniestro}</p>
            <h3 className="text-2xl font-bold text-ink">Score {analisis?.puntaje_riesgo ?? 0} - {analisis?.nivel_riesgo ?? 'Bajo'}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{analisis?.explicacion || 'Sin analisis calculado.'}</p>
          </div>
          <button onClick={onClose} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold hover:bg-slate-50">Cerrar</button>
        </div>

        <Grid title="Resumen del caso" items={[
          ['Ramo', siniestro.ramo], ['Cobertura', siniestro.cobertura], ['Placa Excel', siniestro.placa], ['Ciudad', siniestro.ciudad || siniestro.sucursal],
          ['Estado', siniestro.estado], ['Fecha ocurrencia', siniestro.fecha_siniestro], ['Fecha reporte', siniestro.fecha_reporte],
          ['Dias ocurrencia-reporte', siniestro.dias_ocurrencia_reporte], ['Monto reclamado', siniestro.monto_reclamado],
          ['Monto estimado', siniestro.monto_estimado], ['Monto pagado', siniestro.monto_pagado],
          ['Parte policial Excel', siniestro.numero_parte_policial], ['Docs completos', siniestro.docs_completos ? 'Si' : 'No']
        ]} />
        <Grid title="Poliza, asegurado y proveedor" items={[
          ['Poliza', poliza?.id_poliza], ['Estado poliza', poliza?.estado_poliza], ['Suma asegurada', poliza?.suma_asegurada || siniestro.suma_asegurada],
          ['Asegurado', asegurado?.nombres_asegurado || siniestro.id_asegurado], ['Perfil historico', asegurado?.perfil_riesgo_historico],
          ['Proveedor', proveedor?.nombre_proveedor || siniestro.id_proveedor], ['Restriccion', proveedor?.en_lista_restrictiva ? proveedor?.motivo_restriccion || 'Si' : 'No']
        ]} />

        <Section title="Alertas de posible riesgo">
          <div className="space-y-3">
            {alertas.map((alert) => (
              <div key={alert.id_alerta} className="rounded-lg border border-red-100 bg-red-50 p-4">
                <div className="flex items-center gap-2 font-bold text-red-800"><AlertTriangle size={17} /> {alert.tipo_alerta} - {alert.severidad}</div>
                <p className="mt-2 text-sm text-red-900">{alert.explicacion}</p>
                <p className="mt-1 text-xs text-red-700">Fuente: {alert.fuente_evidencia}. Campo: {alert.campo_detectado}. Esperado: {alert.valor_esperado || '-'} / Encontrado: {alert.valor_encontrado || '-'}</p>
              </div>
            ))}
            {!alertas.length && <p className="text-sm text-slate-500">Sin alertas generadas.</p>}
          </div>
        </Section>

        <Section title="Documentos asociados y PDFs">
          <div className="grid gap-3 md:grid-cols-2">
            {documentos.map((doc) => (
              <div key={doc.id_documento} className="rounded-lg border border-slate-200 p-4 text-sm">
                <p className="font-bold text-ink">{doc.id_documento} - {doc.tipo_documento}</p>
                <p className="mt-1 text-slate-600">{doc.nombre_archivo_pdf || 'Sin nombre de PDF'}</p>
                <p className="mt-1 text-xs text-slate-500">PDF faltante: {doc.pdf_no_encontrado ? 'Si' : 'No'} - No listado en Excel: {doc.documento_no_listado_en_excel ? 'Si' : 'No'}</p>
                {doc.ruta_archivo && (
                  <a
                    className="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 font-bold text-slate-700 hover:bg-slate-50"
                    href={claimsApi.hackiaPdfDownloadUrl(doc.id_documento)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Download size={15} /> Descargar PDF
                  </a>
                )}
              </div>
            ))}
          </div>
        </Section>

        <Section title="Texto extraido de PDFs / OCR">
          <div className="space-y-3">
            {extraidos.map((doc) => (
              <details key={doc.id} className="rounded-lg border border-slate-200 p-4">
                <summary className="cursor-pointer font-bold text-ink"><FileText className="mr-2 inline" size={16} />{doc.nombre_archivo} - {doc.metodo_extraccion}</summary>
                <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-700">{doc.texto_extraido}</pre>
              </details>
            ))}
            {!extraidos.length && <p className="text-sm text-slate-500">Aun no hay PDFs procesados para este siniestro.</p>}
          </div>
        </Section>

        <Grid title="Datos extraidos estructurados" items={[
          ['Facturas', facturas.length], ['Partes policiales', partes_policiales.length], ['Declaraciones', declaraciones.length]
        ]} />
        <Section title="Detalle estructurado de PDFs">
          <StructuredRows title="Facturas" rows={facturas} fields={[
            ['Factura', 'numero_factura'], ['Fecha', 'fecha'], ['Proveedor/taller', 'taller_proveedor'],
            ['RUC', 'ruc'], ['Cliente', 'cliente'], ['Placa', 'placa'], ['Vehiculo', 'vehiculo'],
            ['Subtotal', 'subtotal'], ['IVA', 'iva'], ['Total a pagar', 'total_pagar'],
            ['Caso marcado en PDF', 'caso_marcado'], ['Documento alterado', 'documento_alterado'],
            ['Descripciones', 'descripciones_reparacion']
          ]} />
          <StructuredRows title="Partes policiales" rows={partes_policiales} fields={[
            ['Parte policial', 'numero_parte_policial'], ['Fecha', 'fecha'], ['Hora', 'hora'], ['Lugar', 'lugar'],
            ['Tipo evento', 'tipo_accidente'], ['Consecuencias', 'consecuencias'], ['Clima', 'clima'],
            ['Placa', 'placa'], ['Marca', 'marca'], ['Modelo', 'modelo'], ['Motor', 'motor'], ['Chasis', 'chasis'],
            ['Autoridad/agente', 'autoridad_agente'], ['Narrativa', 'narrativa_accidente'], ['Observaciones', 'observaciones_relevantes']
          ]} />
          <StructuredRows title="Declaraciones de accidente" rows={declaraciones} fields={[
            ['Asegurado', 'asegurado'], ['Telefono', 'telefono'], ['Direccion', 'direccion'], ['Poliza', 'poliza'],
            ['Placa', 'placa'], ['Marca', 'marca'], ['Modelo', 'modelo'], ['Color', 'color'], ['Motor', 'motor'], ['Chasis', 'chasis'],
            ['Fecha accidente', 'fecha_accidente'], ['Hora', 'hora'], ['Lugar', 'lugar'], ['Velocidad', 'velocidad'],
            ['Descripcion', 'descripcion_accidente'], ['Responsable conductor', 'responsable_conductor'],
            ['Datos contrario', 'datos_contrario'], ['Autoridades', 'intervencion_autoridades'], ['Asistencia medica', 'lugar_asistencia_medica']
          ]} />
        </Section>
      </aside>
    </div>
  )
}

function Grid({ title, items }) {
  return (
    <Section title={title}>
      <div className="grid gap-3 md:grid-cols-3">
        {items.map(([label, value]) => (
          <div key={label} className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs font-bold uppercase text-slate-500">{label}</p>
            <p className="mt-1 text-sm font-semibold text-ink">{String(value ?? '-')}</p>
          </div>
        ))}
      </div>
    </Section>
  )
}

function Section({ title, children }) {
  return <section className="mt-6"><h4 className="mb-3 text-lg font-bold text-ink">{title}</h4>{children}</section>
}

function StructuredRows({ title, rows, fields }) {
  return (
    <div className="mb-4 rounded-lg border border-slate-200 p-4">
      <h5 className="font-bold text-ink">{title}</h5>
      <div className="mt-3 space-y-3">
        {rows.map((row, index) => (
          <div key={row.id || index} className="grid gap-2 rounded-lg bg-slate-50 p-3 md:grid-cols-2">
            {fields.map(([label, key]) => (
              <p key={key} className="text-sm"><strong>{label}:</strong> {String(row[key] ?? '-')}</p>
            ))}
          </div>
        ))}
      </div>
      {!rows.length && <p className="text-sm text-slate-500">Sin registros procesados de este tipo.</p>}
    </div>
  )
}
