import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, FileText, Search } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'

const tabs = [
  { id: 'siniestros', label: 'Siniestros' },
  { id: 'polizas', label: 'Pólizas' },
  { id: 'asegurados', label: 'Asegurados' },
  { id: 'proveedores', label: 'Proveedores' },
  { id: 'documentos', label: 'Documentos' },
  { id: 'analisis', label: 'Análisis' }
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
  const [selected, setSelected] = useState(null)
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState('siniestros')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([claimsApi.hackiaClaims(), claimsApi.hackiaTables()])
      .then(([claimsData, tablesData]) => {
        setClaims(claimsData)
        setTables(tablesData)
      })
      .catch((err) => setError(String(err.detail || err.message)))
  }, [])

  const rows = tab === 'siniestros' ? claims : (tables[tab] || [])
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
            <h3 className="text-xl font-bold text-ink">Panel HackIAthon Excel + PDFs</h3>
            <p className="mt-1 text-sm text-slate-600">Cada pestaña refleja la información importada desde las hojas del Excel y los PDFs procesados.</p>
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
      ) : (
        <GenericTable rows={filtered} />
      )}

      {selected && <HackiaDetail detail={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function ClaimsTable({ rows, onOpen }) {
  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-soft">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
                {['Siniestro', 'Ramo', 'Cobertura', 'Placa', 'Estado', 'Proveedor', 'Monto', 'Score', 'Docs', 'PDFs', 'Alertas'].map((label) => (
                <th key={label} className="px-4 py-3 text-left text-xs font-bold uppercase text-slate-500">{label}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((claim) => (
              <tr key={claim.id_siniestro} onClick={() => onOpen(claim.id_siniestro)} className="cursor-pointer hover:bg-blue-50/50">
                <td className="px-4 py-3 text-sm font-bold text-electric">{claim.id_siniestro}</td>
                <td className="px-4 py-3 text-sm">{claim.ramo || '-'}</td>
                <td className="px-4 py-3 text-sm">{claim.cobertura || '-'}</td>
                <td className="px-4 py-3 text-sm">{claim.placa || '-'}</td>
                <td className="px-4 py-3 text-sm">{claim.estado || '-'}</td>
                <td className="px-4 py-3 text-sm">{claim.nombre_proveedor || claim.id_proveedor || '-'}</td>
                <td className="px-4 py-3 text-sm font-semibold">${Number(claim.monto_reclamado || 0).toLocaleString()}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`rounded-full border px-3 py-1 text-xs font-bold ${riskTones[claim.nivel_riesgo] || riskTones.Bajo}`}>
                    {claim.puntaje_riesgo} · {claim.nivel_riesgo}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">{claim.documentos}</td>
                <td className="px-4 py-3 text-sm">{claim.pdfs_procesados}</td>
                <td className="px-4 py-3 text-sm font-bold text-red-700">{claim.alertas}</td>
              </tr>
            ))}
            {!rows.length && <EmptyRow colSpan={11} />}
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
        No hay datos cargados en esta sección. Importa el Excel desde Datos.
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
            <h3 className="text-2xl font-bold text-ink">Score {analisis?.puntaje_riesgo ?? 0} · {analisis?.nivel_riesgo ?? 'Bajo'}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{analisis?.explicacion || 'Sin análisis calculado.'}</p>
          </div>
          <button onClick={onClose} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold hover:bg-slate-50">Cerrar</button>
        </div>

        <Grid title="Resumen del caso" items={[
          ['Ramo', siniestro.ramo], ['Cobertura', siniestro.cobertura], ['Placa Excel', siniestro.placa], ['Ciudad', siniestro.ciudad],
          ['Estado', siniestro.estado], ['Fecha ocurrencia', siniestro.fecha_siniestro], ['Fecha reporte', siniestro.fecha_reporte],
          ['Días ocurrencia-reporte', siniestro.dias_ocurrencia_reporte], ['Monto reclamado', siniestro.monto_reclamado],
          ['Monto estimado', siniestro.monto_estimado], ['Monto pagado', siniestro.monto_pagado],
          ['Parte policial Excel', siniestro.numero_parte_policial], ['Docs completos', siniestro.docs_completos ? 'Sí' : 'No']
        ]} />
        <Grid title="Póliza, asegurado y proveedor" items={[
          ['Póliza', poliza?.id_poliza], ['Estado póliza', poliza?.estado_poliza], ['Suma asegurada', poliza?.suma_asegurada || siniestro.suma_asegurada],
          ['Asegurado', asegurado?.nombres_asegurado || siniestro.id_asegurado], ['Perfil histórico', asegurado?.perfil_riesgo_historico],
          ['Proveedor', proveedor?.nombre_proveedor || siniestro.id_proveedor], ['Restricción', proveedor?.en_lista_restrictiva ? proveedor?.motivo_restriccion || 'Sí' : 'No']
        ]} />

        <Section title="Alertas de posible riesgo">
          <div className="space-y-3">
            {alertas.map((alert) => (
              <div key={alert.id_alerta} className="rounded-lg border border-red-100 bg-red-50 p-4">
                <div className="flex items-center gap-2 font-bold text-red-800"><AlertTriangle size={17} /> {alert.tipo_alerta} · {alert.severidad}</div>
                <p className="mt-2 text-sm text-red-900">{alert.explicacion}</p>
                <p className="mt-1 text-xs text-red-700">Fuente: {alert.fuente_evidencia}. Campo: {alert.campo_detectado}. Esperado: {alert.valor_esperado || '-'} / Encontrado: {alert.valor_encontrado || '-'}</p>
              </div>
            ))}
            {!alertas.length && <p className="text-sm text-slate-500">Sin alertas generadas.</p>}
          </div>
        </Section>

        <Section title="Documentos asociados">
          <div className="grid gap-3 md:grid-cols-2">
            {documentos.map((doc) => (
              <div key={doc.id_documento} className="rounded-lg border border-slate-200 p-4 text-sm">
                <p className="font-bold text-ink">{doc.id_documento} · {doc.tipo_documento}</p>
                <p className="mt-1 text-slate-600">{doc.nombre_archivo_pdf || 'Sin nombre de PDF'}</p>
                <p className="mt-1 text-xs text-slate-500">PDF faltante: {doc.pdf_no_encontrado ? 'Sí' : 'No'} · No listado en Excel: {doc.documento_no_listado_en_excel ? 'Sí' : 'No'}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Texto extraído de PDFs / OCR">
          <div className="space-y-3">
            {extraidos.map((doc) => (
              <details key={doc.id} className="rounded-lg border border-slate-200 p-4">
                <summary className="cursor-pointer font-bold text-ink"><FileText className="mr-2 inline" size={16} />{doc.nombre_archivo} · {doc.metodo_extraccion}</summary>
                <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-700">{doc.texto_extraido}</pre>
              </details>
            ))}
            {!extraidos.length && <p className="text-sm text-slate-500">Aún no hay PDFs procesados para este siniestro.</p>}
          </div>
        </Section>

        <Grid title="Datos extraídos estructurados" items={[
          ['Facturas', facturas.length], ['Partes policiales', partes_policiales.length], ['Declaraciones', declaraciones.length]
        ]} />
        <Section title="Detalle estructurado de PDFs">
          <StructuredRows
            title="Facturas"
            rows={facturas}
            fields={[
              ['Factura', 'numero_factura'], ['Fecha', 'fecha'], ['Proveedor/taller', 'taller_proveedor'],
              ['RUC', 'ruc'], ['Cliente', 'cliente'], ['Placa', 'placa'], ['Vehiculo', 'vehiculo'],
              ['Subtotal', 'subtotal'], ['IVA', 'iva'], ['Total a pagar', 'total_pagar'],
              ['Caso marcado en PDF', 'caso_marcado'], ['Documento alterado', 'documento_alterado'],
              ['Descripciones', 'descripciones_reparacion']
            ]}
          />
          <StructuredRows
            title="Partes policiales"
            rows={partes_policiales}
            fields={[
              ['Parte policial', 'numero_parte_policial'], ['Fecha', 'fecha'], ['Hora', 'hora'], ['Lugar', 'lugar'],
              ['Tipo evento', 'tipo_accidente'], ['Consecuencias', 'consecuencias'], ['Clima', 'clima'],
              ['Placa', 'placa'], ['Marca', 'marca'], ['Modelo', 'modelo'], ['Motor', 'motor'], ['Chasis', 'chasis'],
              ['Autoridad/agente', 'autoridad_agente'], ['Narrativa', 'narrativa_accidente'], ['Observaciones', 'observaciones_relevantes']
            ]}
          />
          <StructuredRows
            title="Declaraciones de accidente"
            rows={declaraciones}
            fields={[
              ['Asegurado', 'asegurado'], ['Telefono', 'telefono'], ['Direccion', 'direccion'], ['Poliza', 'poliza'],
              ['Placa', 'placa'], ['Marca', 'marca'], ['Modelo', 'modelo'], ['Color', 'color'], ['Motor', 'motor'], ['Chasis', 'chasis'],
              ['Fecha accidente', 'fecha_accidente'], ['Hora', 'hora'], ['Lugar', 'lugar'], ['Velocidad', 'velocidad'],
              ['Descripcion', 'descripcion_accidente'], ['Responsable segun conductor', 'responsable_conductor'],
              ['Datos del contrario', 'datos_contrario'], ['Autoridades', 'intervencion_autoridades'], ['Asistencia medica', 'lugar_asistencia_medica']
            ]}
          />
        </Section>
      </aside>
    </div>
  )
}

function Section({ title, children }) {
  return <section className="mt-6"><h4 className="mb-3 text-sm font-bold uppercase text-slate-500">{title}</h4>{children}</section>
}

function StructuredRows({ title, rows, fields }) {
  return (
    <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50/70 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h5 className="text-sm font-bold text-ink">{title}</h5>
        <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-500">{rows.length}</span>
      </div>
      {!rows.length && <p className="text-sm text-slate-500">Sin registros procesados de este tipo.</p>}
      <div className="space-y-3">
        {rows.map((row, index) => (
          <div key={`${title}-${row.id || index}`} className="rounded-lg bg-white p-3 shadow-sm">
            <div className="grid gap-2 md:grid-cols-2">
              {fields.map(([label, key]) => {
                const value = row[key]
                if (value === null || value === undefined || value === '') return null
                return (
                  <div key={key} className={String(value).length > 90 ? 'md:col-span-2' : ''}>
                    <p className="text-[11px] font-bold uppercase text-slate-400">{label}</p>
                    <p className="whitespace-pre-wrap break-words text-sm text-slate-800">{formatStructuredValue(value)}</p>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatStructuredValue(value) {
  if (typeof value === 'boolean') return value ? 'Si' : 'No'
  return String(value)
}

function Grid({ title, items }) {
  return (
    <Section title={title}>
      <div className="grid gap-2 md:grid-cols-2">
        {items.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[150px_1fr] gap-3 border-b border-slate-100 py-2 text-sm">
            <span className="font-semibold text-slate-500">{label}</span>
            <span className="text-slate-800">{String(value ?? '-')}</span>
          </div>
        ))}
      </div>
    </Section>
  )
}
