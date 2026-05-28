import { UploadCloud } from 'lucide-react'
import { useState } from 'react'
import { claimsApi } from '../api/claimsApi.js'
import CsvValidationModal, { buildUploadErrorModal } from './CsvValidationModal.jsx'

export default function UploadDataset({ onUploaded }) {
  const [message, setMessage] = useState('')
  const [modal, setModal] = useState(null)

  async function onFile(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setMessage('Validando CSV...')
    try {
      const response = await claimsApi.upload(file)
      setMessage(`${response.message} Insertados: ${response.result?.inserted ?? 0}.`)
      onUploaded?.()
    } catch (error) {
      setMessage('')
      setModal(buildUploadErrorModal(error))
    }
  }

  return (
    <>
      <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white p-4 text-sm shadow-soft hover:border-electric">
        <UploadCloud className="text-electric" size={22} />
        <span className="font-semibold text-ink">Cargar CSV de prueba</span>
        <input type="file" accept=".csv" className="hidden" onChange={onFile} />
        {message && <span className="text-slate-500">{message}</span>}
      </label>
      <CsvValidationModal modal={modal} onClose={() => setModal(null)} />
    </>
  )
}
