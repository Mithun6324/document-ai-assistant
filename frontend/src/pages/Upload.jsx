import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { UploadCloud } from 'lucide-react'
import { documentsApi } from '../services/api'

const STAGES = ['queued', 'extracting', 'cleaning', 'chunking', 'embedding', 'indexing', 'ready']

export default function UploadPage() {
  const [drag, setDrag] = useState(false)
  const [uploadPct, setUploadPct] = useState(0)
  const [doc, setDoc] = useState(null)
  const [error, setError] = useState('')
  const [status, setStatus] = useState(null)
  const inputRef = useRef(null)
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: (file) => documentsApi.upload(file, setUploadPct),
    onSuccess: (res) => {
      setDoc(res.data)
      setStatus(res.data)
      setError('')
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (err) => {
      setError(err.response?.data?.detail || 'Upload failed')
    },
  })

  useEffect(() => {
    if (!doc?.id) return
    if (doc.status === 'ready' || doc.status === 'failed' || doc.duplicate) return
    const timer = setInterval(async () => {
      try {
        const res = await documentsApi.status(doc.id)
        setStatus(res.data)
        if (['ready', 'failed'].includes(res.data.status)) {
          clearInterval(timer)
          qc.invalidateQueries({ queryKey: ['documents'] })
          qc.invalidateQueries({ queryKey: ['dashboard'] })
        }
      } catch {
        // ignore transient errors
      }
    }, 2000)
    return () => clearInterval(timer)
  }, [doc, qc])

  function onFiles(files) {
    const file = files?.[0]
    if (!file) return
    const name = file.name.toLowerCase()
    if (!name.endsWith('.pdf') && !name.endsWith('.docx')) {
      setError('Only PDF and DOCX files are supported')
      return
    }
    setError('')
    setUploadPct(0)
    setDoc(null)
    setStatus(null)
    mutation.mutate(file)
  }

  const progress = status?.progress_percent ?? uploadPct
  const stage = status?.progress_stage || (mutation.isPending ? 'uploading' : null)

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Upload Documents</h1>
        <p className="text-sm text-slate-400">PDF and DOCX · max 25 MB</p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDrag(true)
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDrag(false)
          onFiles(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition ${
          drag ? 'border-indigo-400 bg-indigo-500/10' : 'border-slate-700 bg-slate-900/40 hover:border-slate-500'
        }`}
      >
        <UploadCloud className="mx-auto mb-3 text-indigo-300" size={36} />
        <div className="font-medium">Drag & drop files here</div>
        <div className="text-sm text-slate-400 mt-1">or click to browse</div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(e) => onFiles(e.target.files)}
        />
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}

      {(mutation.isPending || status) && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
          <div className="flex justify-between text-sm">
            <span>{doc?.original_filename || 'Uploading…'}</span>
            <span className="text-slate-400">{progress}%</span>
          </div>
          <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
          <div className="text-xs text-slate-400 capitalize">Stage: {stage || '—'}</div>
          <div className="flex flex-wrap gap-2 text-[11px]">
            {STAGES.map((s) => (
              <span
                key={s}
                className={`rounded-full px-2 py-0.5 border ${
                  stage === s ? 'border-amber-400 text-amber-300' : 'border-slate-700 text-slate-500'
                }`}
              >
                {s}
              </span>
            ))}
          </div>
          {doc?.duplicate && (
            <div className="text-sm text-amber-300">
              This file was already uploaded.{' '}
              <Link className="underline" to={`/documents/${doc.id}`}>Open existing document</Link>
            </div>
          )}
          {status?.status === 'ready' && (
            <div className="text-sm text-emerald-300">
              Ready · {status.chunk_count} chunks ·{' '}
              <Link className="underline" to={`/chat?doc=${doc.id}`}>Ask questions</Link>
            </div>
          )}
          {status?.status === 'failed' && (
            <div className="text-sm text-red-300">{status.processing_error || 'Processing failed'}</div>
          )}
        </div>
      )}
    </div>
  )
}
