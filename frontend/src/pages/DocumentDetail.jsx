import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { documentsApi } from '../services/api'

export default function DocumentDetail() {
  const { id } = useParams()
  const docQuery = useQuery({
    queryKey: ['document', id],
    queryFn: async () => (await documentsApi.get(id)).data,
  })
  const qQuery = useQuery({
    queryKey: ['document-questions', id],
    queryFn: async () => (await documentsApi.questions(id)).data,
  })
  const sQuery = useQuery({
    queryKey: ['suggested', id],
    queryFn: async () => (await documentsApi.suggested(id)).data,
    enabled: docQuery.data?.status === 'ready',
  })

  const doc = docQuery.data

  if (docQuery.isLoading) return <div className="text-slate-400">Loading…</div>
  if (!doc) return <div className="text-red-300">Document not found</div>

  return (
    <div className="space-y-6 max-w-4xl">
      <Link to="/documents" className="text-sm text-slate-400 hover:text-white">← Back</Link>
      <div>
        <h1 className="text-2xl font-semibold">{doc.original_filename}</h1>
        <p className="text-sm text-slate-400 mt-1 capitalize">
          {doc.status} · {doc.page_count} pages · {doc.chunk_count} chunks · uploaded {new Date(doc.created_at).toLocaleString()}
        </p>
      </div>

      {doc.status === 'ready' && (
        <div>
          <h2 className="font-medium mb-2">Suggested questions</h2>
          <div className="flex flex-wrap gap-2">
            {(sQuery.data || []).map((q) => (
              <Link
                key={q}
                to={`/chat?doc=${id}&q=${encodeURIComponent(q)}`}
                className="rounded-full border border-slate-700 px-3 py-1 text-sm hover:border-indigo-400"
              >
                {q}
              </Link>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-medium">Questions asked about this document</h2>
          <Link to={`/chat?doc=${id}`} className="text-sm text-indigo-300">Ask new question →</Link>
        </div>
        <div className="space-y-2">
          {(qQuery.data || []).map((item) => (
            <Link
              key={item.message_id}
              to={`/chat?c=${item.conversation_id}`}
              className="block rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 hover:bg-slate-800/40"
            >
              <div className="text-sm">{item.question}</div>
              {item.answer_preview && (
                <div className="text-xs text-slate-400 mt-1 line-clamp-2">{item.answer_preview}</div>
              )}
              <div className="text-[11px] text-slate-500 mt-1">{new Date(item.asked_at).toLocaleString()}</div>
            </Link>
          ))}
          {!qQuery.isLoading && (qQuery.data || []).length === 0 && (
            <p className="text-sm text-slate-400">No questions yet for this document.</p>
          )}
        </div>
      </div>
    </div>
  )
}
