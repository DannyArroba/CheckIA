import { useEffect, useRef, useState } from 'react'
import { Bot, Cpu, FileSpreadsheet, Files, LoaderCircle, MessageSquarePlus, SearchCheck, Send, ShieldCheck, Sparkles, Trash2, UserRound } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import { HackiaDetail } from '../pages/Hackia.jsx'

const quickQuestions = [
  '¿Cuáles son los 10 siniestros con mayor riesgo?',
  '¿Qué proveedores concentran más alertas?',
  '¿Qué ciudades tienen más casos rojos?',
  '¿Qué documentos faltan en los casos críticos?',
  '¿Qué casos tienen montos atípicos?',
  '¿Qué siniestros ocurrieron cerca del inicio de la póliza?',
  '¿Qué patrones se repiten?',
  'Genera un resumen ejecutivo.',
  'Recomienda qué casos revisar primero.'
]

const welcome = {
  role: 'agente',
  text: 'Hola, soy el agente CheckIA. Puedo ayudarte a revisar posibles señales de riesgo en siniestros, siempre como apoyo para análisis humano.',
  provider: 'sistema',
  relatedClaims: []
}

export default function AgentChat() {
  const [messages, setMessages] = useState([welcome])
  const [conversations, setConversations] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingMode, setLoadingMode] = useState('simple')
  const [status, setStatus] = useState(null)
  const [selectedClaim, setSelectedClaim] = useState(null)
  const [uploadStatus, setUploadStatus] = useState('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    claimsApi.agentStatus().then(setStatus).catch(() => setStatus({ available: false, model: 'checkia-gemma' }))
    loadConversations()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  async function loadConversations() {
    const list = await claimsApi.agentConversations().catch(() => [])
    setConversations(list)
    if (!conversationId && list[0]) openConversation(list[0].conversation_id)
  }

  async function openConversation(id) {
    setConversationId(id)
    const rows = await claimsApi.agentHistory(id).catch(() => [])
    if (!rows.length) {
      setMessages([welcome])
      return
    }
    setMessages(rows.map((row) => ({
      role: row.role,
      text: row.message_text,
      provider: row.provider,
      relatedClaims: extractClaimIds(row.message_text)
    })))
  }

  async function newChat() {
    const created = await claimsApi.createConversation()
    setConversationId(created.conversation_id)
    setMessages([welcome])
    await loadConversations()
  }

  async function deleteConversation(id) {
    await claimsApi.deleteConversation(id)
    if (id === conversationId) {
      setConversationId(null)
      setMessages([welcome])
    }
    await loadConversations()
  }

  async function send(text = input) {
    const trimmed = text.trim()
    if (!trimmed || loading) return
    const activeConversation = conversationId || (await claimsApi.createConversation()).conversation_id
    setConversationId(activeConversation)
    setMessages((current) => [...current, { role: 'usuario', text: trimmed, relatedClaims: [] }])
    setInput('')
    setLoadingMode(needsAnalysisLoading(trimmed) ? 'analysis' : 'simple')
    setLoading(true)
    try {
      const response = await claimsApi.chat(trimmed, activeConversation)
      setMessages((current) => [
        ...current,
        {
          role: 'agente',
          text: response.answer,
          provider: response.provider || 'reglas',
          relatedClaims: response.related_claims || [],
          suggestions: response.suggestions || []
        }
      ])
      await loadConversations()
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: 'agente',
          text: 'No pude conectar con el backend. Verifica que FastAPI esté ejecutándose.',
          provider: 'error',
          relatedClaims: []
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  async function openClaim(claimId) {
    const detail = claimId.startsWith('SIN-') ? await claimsApi.hackiaClaim(claimId) : await claimsApi.claim(claimId)
    setSelectedClaim(detail)
  }

  async function uploadExcel(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setUploadStatus('Importando Excel...')
    try {
      const result = await claimsApi.uploadHackiaExcel(file)
      setUploadStatus(`Excel cargado: ${result.records.siniestros} siniestros y ${result.records.documentos} documentos.`)
    } catch (error) {
      setUploadStatus(`No se pudo cargar Excel: ${error.detail || error.message}`)
    }
  }

  async function uploadPdfs(event) {
    const files = event.target.files
    event.target.value = ''
    if (!files?.length) return
    setUploadStatus('Procesando PDFs...')
    try {
      const result = await claimsApi.uploadHackiaPdfs(files)
      const rejected = result.details?.filter((item) => item.rechazado).length || 0
      setUploadStatus(`PDFs procesados: ${result.stats.pdfs_procesados}. Omitidos sin SIN/DOC: ${rejected}.`)
    } catch (error) {
      setUploadStatus(`No se pudieron procesar PDFs: ${error.detail || error.message}`)
    }
  }

  return (
    <div className="grid h-[calc(100vh-140px)] min-h-[560px] gap-5 xl:grid-cols-[280px_1fr_280px]">
      <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-soft">
        <button onClick={newChat} className="mb-4 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg bg-electric px-3 text-sm font-semibold text-white hover:bg-blue-700">
          <MessageSquarePlus size={17} /> Nuevo chat
        </button>
        <div className="space-y-2">
          {conversations.length === 0 && <p className="text-sm text-slate-500">Aún no hay conversaciones guardadas.</p>}
          {conversations.map((item) => (
            <div key={item.conversation_id} className={`group flex items-center gap-2 rounded-lg border p-2 ${item.conversation_id === conversationId ? 'border-electric bg-blue-50' : 'border-slate-200'}`}>
              <button onClick={() => openConversation(item.conversation_id)} className="min-w-0 flex-1 text-left">
                <p className="truncate text-sm font-bold text-ink">{item.title}</p>
                <p className="text-xs text-slate-500">{item.message_count} mensajes</p>
              </button>
              <button onClick={() => deleteConversation(item.conversation_id)} className="grid h-8 w-8 place-items-center rounded text-slate-400 hover:bg-white hover:text-red-600" title="Eliminar chat">
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="flex min-h-0 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-soft">
        <div className="flex min-h-0 w-full flex-col">
          <div className="border-b border-slate-200 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-ink">Chat de análisis</h3>
                <p className="text-xs text-slate-500">Las respuestas son apoyo para revisión humana, no decisiones finales.</p>
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                <Cpu size={15} /> {status?.available ? `Ollama conectado: ${status.model}` : 'Ollama sin conexión activa'}
              </div>
            </div>
            {loading && loadingMode === 'analysis' && <TopLoadingBar />}
          </div>

          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain p-5">
            {messages.map((message, index) => (
              <div key={index} className={`flex items-start gap-3 ${message.role === 'usuario' ? 'justify-end' : 'justify-start'}`}>
                {message.role !== 'usuario' && <Avatar icon={Bot} tone="agent" />}
                <div className={`max-w-[82%] rounded-lg px-4 py-3 text-sm leading-6 ${message.role === 'usuario' ? 'bg-electric text-white' : 'bg-slate-100 text-slate-800'}`}>
                  <MessageText text={message.text} onClaimClick={openClaim} />
                  {message.role !== 'usuario' && (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-white px-2 py-1 text-[11px] font-bold uppercase text-slate-500">{message.provider}</span>
                      {(message.relatedClaims || []).filter((claimId) => !message.text.includes(claimId)).map((claimId) => (
                        <button key={claimId} onClick={() => openClaim(claimId)} className="rounded-full bg-blue-100 px-2 py-1 text-xs font-bold text-blue-800 hover:bg-blue-200">
                          {claimId}
                        </button>
                      ))}
                      {(message.suggestions || []).map((suggestion) => (
                        <button key={suggestion} onClick={() => send(suggestion)} className="rounded-full border border-blue-200 bg-white px-2 py-1 text-xs font-bold text-blue-700 hover:bg-blue-50">
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {message.role === 'usuario' && <Avatar icon={UserRound} tone="user" />}
              </div>
            ))}
            {loading && (loadingMode === 'analysis' ? <LoadingBubble provider={status?.available ? 'ollama' : 'reglas'} /> : <ThinkingBubble />)}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-slate-200 p-4">
            <div className="flex gap-3">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                  }
                }}
                rows={1}
                className="max-h-32 min-h-11 flex-1 resize-none rounded-lg border border-slate-200 px-4 py-2.5 outline-none focus:border-electric"
                placeholder={loading ? 'CheckIA está preparando la respuesta...' : 'Pregunta sobre riesgos, proveedores, documentos o patrones'}
                disabled={loading}
              />
              <button onClick={() => send()} className="grid h-11 w-11 place-items-center rounded-lg bg-electric text-white hover:bg-blue-700 disabled:opacity-60" disabled={loading} aria-label="Enviar">
                {loading ? <LoaderCircle className="animate-spin" size={18} /> : <Send size={18} />}
              </button>
            </div>
          </div>
        </div>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-soft">
        <div className="mb-4 flex items-center gap-2 font-bold text-ink"><Sparkles size={18} /> Preguntas rápidas</div>
        <div className="mb-4 grid grid-cols-2 gap-2">
          <label className="grid min-h-10 cursor-pointer place-items-center rounded-lg border border-slate-200 text-xs font-bold text-slate-600 hover:border-electric hover:text-electric" title="Cargar Excel HackIAthon">
            <FileSpreadsheet size={17} />
            <input type="file" accept=".xlsx,.xls,.xlsm" className="hidden" onChange={uploadExcel} />
          </label>
          <label className="grid min-h-10 cursor-pointer place-items-center rounded-lg border border-slate-200 text-xs font-bold text-slate-600 hover:border-electric hover:text-electric" title="Cargar PDFs">
            <Files size={17} />
            <input type="file" accept=".pdf" multiple className="hidden" onChange={uploadPdfs} />
          </label>
        </div>
        {uploadStatus && <p className="mb-3 rounded-lg bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-900">{uploadStatus}</p>}
        <div className="space-y-2">
          {quickQuestions.map((question) => (
            <button key={question} onClick={() => send(question)} disabled={loading} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-sm hover:border-electric hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50">
              {question}
            </button>
          ))}
        </div>
      </aside>
      {selectedClaim?.siniestro
        ? <HackiaDetail detail={selectedClaim} onClose={() => setSelectedClaim(null)} />
        : null}
    </div>
  )
}

function TopLoadingBar() {
  return (
    <div className="mt-4 h-1 overflow-hidden rounded-full bg-slate-100">
      <div className="h-full w-1/2 animate-[loadingSlide_1.25s_ease-in-out_infinite] rounded-full bg-electric" />
    </div>
  )
}

function ThinkingBubble() {
  return (
    <div className="flex items-start gap-3">
      <Avatar icon={Bot} tone="agent" />
      <div className="inline-flex max-w-[82%] items-center gap-2 rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">
        <LoaderCircle className="animate-spin text-electric" size={16} />
        <span className="font-medium">Pensando</span>
        <TypingDots />
      </div>
    </div>
  )
}

function LoadingBubble({ provider }) {
  const steps = provider === 'ollama'
    ? ['Interpretando la pregunta', 'Revisando si requiere datos', 'Generando respuesta con Ollama']
    : ['Interpretando la pregunta', 'Preparando respuesta breve', 'Mostrando resultado']

  return (
    <div className="flex items-start gap-3">
      <Avatar icon={Bot} tone="agent" />
      <div className="max-w-[82%] rounded-lg border border-blue-100 bg-blue-50 px-4 py-4 text-sm text-blue-950 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="relative grid h-12 w-12 shrink-0 place-items-center rounded-full bg-white">
            <span className="absolute h-12 w-12 animate-ping rounded-full bg-blue-200 opacity-60" />
            <LoaderCircle className="relative animate-spin text-electric" size={26} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="font-bold text-ink">Analizando siniestros...</p>
              <TypingDots />
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Espera un momento. CheckIA está interpretando tu mensaje y decidirá si necesita consultar datos o responder directo.
            </p>
            <div className="mt-3 grid gap-2">
              {steps.map((step, index) => (
                <div key={step} className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                  {index < 2 ? <SearchCheck size={14} className="text-emerald-600" /> : <ShieldCheck size={14} className="text-electric" />}
                  {step}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-electric [animation-delay:-0.2s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-electric [animation-delay:-0.1s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-electric" />
    </span>
  )
}

function MessageText({ text, onClaimClick }) {
  const lines = prepareMessageText(text).split('\n')
  return (
    <div className="space-y-2 text-[13.5px] leading-6">
      {lines.map((line, index) => {
        const trimmed = line.trim()
        if (!trimmed) return <div key={index} className="h-1" />
        if (/^#{1,3}\s+/.test(trimmed)) {
          return <p key={index} className="pb-1 text-base font-bold text-ink"><InlineText text={trimmed.replace(/^#{1,3}\s+/, '')} onClaimClick={onClaimClick} /></p>
        }
        if (/^(\*\*[^*]+:\*\*|[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚáéíóúÑñ ]+)$/.test(trimmed)) {
          return <p key={index} className="pt-1 font-bold text-slate-900"><InlineText text={trimmed.replace(/^\*\*|\*\*$/g, '')} onClaimClick={onClaimClick} /></p>
        }
        if (/^[-*]\s+/.test(trimmed)) {
          return (
            <div key={index} className="flex gap-2">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />
              <p className="min-w-0 flex-1"><InlineText text={trimmed.replace(/^[-*]\s+/, '')} onClaimClick={onClaimClick} /></p>
            </div>
          )
        }
        return <p key={index}><InlineText text={trimmed} onClaimClick={onClaimClick} /></p>
      })}
    </div>
  )
}

function prepareMessageText(text) {
  return text
    .replace(/\r\n/g, '\n')
    .replace(/\s*(#{1,3}\s+)/g, '\n$1')
    .replace(/\s+\*\s+/g, '\n- ')
    .replace(/\s+(\*\*(?:Resumen|Datos clave|Señales detectadas|Senales detectadas|Lectura predictiva|Siguiente paso|Recomendaciones|Documentos|Análisis predictivo previo|Analisis predictivo previo):?\*\*)/gi, '\n\n$1\n')
    .replace(/\s+(Score|Ciudad|Proveedor|Monto|Señales|Senales|Documentos|Recomendación|Recomendacion|Reglas|Modelo ML|Modelo|Anomalía|Anomalia|NLP):/g, '\n$1:')
    .replace(/\s+(Análisis predictivo previo|Analisis predictivo previo):/gi, '\n\n**Análisis predictivo previo**\n')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function InlineText({ text, onClaimClick }) {
  const parts = text.split(/(\*\*[^*]+\*\*|SIN-\d{4,6})/g)
  return parts.map((part, index) => {
    if (/^SIN-\d{4,6}$/.test(part)) {
      return (
        <button key={`${part}-${index}`} onClick={() => onClaimClick(part)} className="mx-0.5 rounded bg-blue-100 px-1.5 py-0.5 font-bold text-blue-800 hover:bg-blue-200">
          {part}
        </button>
      )
    }
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      return <strong key={`${part}-${index}`} className="font-bold text-slate-900">{part.slice(2, -2)}</strong>
    }
    return <span key={`${part}-${index}`}>{part}</span>
  })
}

function Avatar({ icon: Icon, tone }) {
  return <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${tone === 'agent' ? 'bg-ink text-white' : 'bg-slate-200 text-slate-700'}`}><Icon size={18} /></div>
}

function extractClaimIds(text) {
  return [...new Set((text.match(/SIN-\d{4,6}/g) || []))]
}

function needsAnalysisLoading(text) {
  const normalized = text.toLowerCase()
  const terms = [
    'caso', 'casos', 'siniestro', 'siniestros', 'riesgo', 'proveedor', 'proveedores',
    'documento', 'documentos', 'monto', 'montos', 'ciudad', 'ciudades', 'seguimiento',
    'estado', 'poliza', 'póliza', 'score', 'alerta', 'alertas', 'resumen', 'top',
    'analisis', 'análisis', 'informe', 'reporte', 'patron', 'patrón', 'clm-'
  ]
  return terms.some((term) => normalized.includes(term))
}
