import { UploadCloud } from 'lucide-react'
import { useState } from 'react'
import { claimsApi } from '../api/claimsApi.js'

export default function UploadDataset() {
  const [message, setMessage] = useState('')
  async function onFile(event) {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const response = await claimsApi.upload(file)
      setMessage(response.message)
    } catch {
      setMessage('No se pudo cargar el archivo. Usa un CSV y verifica el backend.')
    }
  }
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white p-4 text-sm shadow-soft hover:border-electric">
      <UploadCloud className="text-electric" size={22} />
      <span className="font-semibold text-ink">Cargar CSV de prueba</span>
      <input type="file" accept=".csv" className="hidden" onChange={onFile} />
      {message && <span className="text-slate-500">{message}</span>}
    </label>
  )
}
