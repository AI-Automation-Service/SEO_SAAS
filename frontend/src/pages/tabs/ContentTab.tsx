import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FileText, RefreshCw, CheckCircle, ShieldAlert, Shield,
  ChevronDown, Wand2, Pencil, X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { keywordsApi, articleApi, improveApi, getErrorMessage } from '@/api/client'
import type { ArticleOut, PlagiarismStatus } from '@/types/api'
import { cn } from '@/lib/utils'

interface ContentTabProps {
  projectName: string
}

const PLAGIARISM_BADGE: Record<PlagiarismStatus, { label: string; className: string; Icon: typeof Shield }> = {
  skipped:   { label: 'Not checked',       className: 'bg-slate-100 text-slate-500',    Icon: Shield },
  clean:     { label: 'Original',          className: 'bg-emerald-100 text-emerald-700', Icon: Shield },
  flagged:   { label: 'Plagiarism detected', className: 'bg-red-100 text-red-600',      Icon: ShieldAlert },
  rewritten: { label: 'Auto-rewritten',    className: 'bg-blue-100 text-blue-700',       Icon: Shield },
}

export function ContentTab({ projectName }: ContentTabProps) {
  const qc = useQueryClient()
  const [keyword, setKeyword] = useState('')
  const [selectedCluster, setSelectedCluster] = useState('')
  const [result, setResult] = useState<ArticleOut | null>(null)
  const [applyDone, setApplyDone] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editedContent, setEditedContent] = useState('')

  const { data: keywords = [] } = useQuery({
    queryKey: ['keywords', projectName],
    queryFn: () => keywordsApi.list(projectName),
  })

  const clusters = [...new Set(
    keywords
      .filter((k) => k.cluster && k.is_hub)
      .map((k) => k.cluster as string)
  )].sort()

  const generateMut = useMutation({
    mutationFn: () =>
      articleApi.generate(projectName, {
        keyword: keyword.trim(),
        cluster_name: selectedCluster || undefined,
      }),
    onSuccess: (data) => {
      setResult(data)
      setEditedContent(data.content_html ?? '')
      setApplyDone(false)
      setEditing(false)
      toast.success('Article generated — ready to review.')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const applyMut = useMutation({
    mutationFn: () =>
      improveApi.apply(projectName, result!.change_id, editing ? editedContent : undefined),
    onSuccess: () => {
      setApplyDone(true)
      setEditing(false)
      toast.success('Draft published to WordPress.')
      qc.invalidateQueries({ queryKey: ['improve-history', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const plagStatus = (result?.plagiarism_status ?? 'skipped') as PlagiarismStatus
  const plagBadge = PLAGIARISM_BADGE[plagStatus]
  const PlagIcon = plagBadge.Icon

  return (
    <div className="space-y-5 max-w-2xl">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-slate-900">Article Writer</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Generate a full SEO article in two phases. It lands in the Change Queue as a WordPress draft — review before publishing.
        </p>
      </div>

      {/* Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1.5">
            Target keyword <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="e.g. best espresso machines 2025"
            disabled={generateMut.isPending}
            className="w-full text-sm px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-emerald-400 focus:border-emerald-400 disabled:opacity-60"
          />
        </div>

        {clusters.length > 0 && (
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">
              Link to cluster hub <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <div className="relative">
              <select
                value={selectedCluster}
                onChange={(e) => setSelectedCluster(e.target.value)}
                disabled={generateMut.isPending}
                className="w-full text-sm px-3 py-2 pr-8 rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-400 focus:border-emerald-400 appearance-none disabled:opacity-60"
              >
                <option value="">— No cluster (standalone article) —</option>
                {clusters.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <ChevronDown size={14} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            </div>
          </div>
        )}

        <button
          type="button"
          onClick={() => generateMut.mutate()}
          disabled={!keyword.trim() || generateMut.isPending}
          className={cn(
            'w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer',
            !keyword.trim() || generateMut.isPending
              ? 'bg-slate-100 text-slate-300 cursor-not-allowed'
              : 'bg-emerald-600 text-white hover:bg-emerald-700',
          )}
        >
          {generateMut.isPending
            ? <><RefreshCw size={14} className="animate-spin" /> Generating article…</>
            : <><Wand2 size={14} /> Generate Article</>}
        </button>

        {generateMut.isPending && (
          <div className="space-y-1.5">
            {[
              'Phase 1 — Outline + first half',
              'Phase 2 — Completion + final polish',
              'Plagiarism check via Copyscape',
            ].map((label) => (
              <div key={label} className="flex items-center gap-2 text-xs text-slate-500">
                <RefreshCw size={10} className="animate-spin text-emerald-400 shrink-0" />
                {label}
              </div>
            ))}
            <p className="text-[10px] text-slate-400 pt-1">
              Usually takes 60–120 seconds for a ~2,000-word article.
            </p>
          </div>
        )}
      </div>

      {/* Result card */}
      {result && !generateMut.isPending && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          {/* Result header */}
          <div className="flex items-center gap-3 px-5 py-3.5 border-b border-slate-100 bg-slate-50">
            <FileText size={14} className="text-slate-500 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-800 truncate">{result.draft_title}</p>
              <p className="text-[10px] text-slate-400 font-mono">/{result.draft_slug}</p>
            </div>
            <span className="text-[10px] text-slate-400 shrink-0">
              {result.draft_word_count.toLocaleString()} words
            </span>
          </div>

          <div className="p-5 space-y-4">
            {/* Plagiarism badge */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 font-medium">Plagiarism check:</span>
              <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', plagBadge.className)}>
                <PlagIcon size={11} />
                {plagBadge.label}
                {result.plagiarism_score != null && ` · ${Math.round(result.plagiarism_score)}%`}
              </span>
            </div>

            {plagStatus === 'flagged' && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                <ShieldAlert size={13} className="shrink-0 mt-0.5" />
                <span>
                  Plagiarism score exceeds the allowed threshold. The article was not queued.
                  Try regenerating with a more specific angle, or use a different keyword framing.
                </span>
              </div>
            )}

            {plagStatus !== 'flagged' && (
              <>
                {/* Preview / Editor */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-medium text-slate-500">
                      {editing ? 'Edit content (HTML)' : 'Content preview'}
                    </p>
                    {!applyDone && !editing && (
                      <button
                        type="button"
                        onClick={() => setEditing(true)}
                        className="inline-flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                      >
                        <Pencil size={10} /> Edit
                      </button>
                    )}
                    {editing && (
                      <button
                        type="button"
                        onClick={() => setEditing(false)}
                        className="inline-flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                      >
                        <X size={10} /> Cancel edit
                      </button>
                    )}
                  </div>

                  {editing ? (
                    <textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      className="w-full h-80 text-xs font-mono border border-slate-200 rounded-lg p-3 text-slate-700 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-emerald-400 focus:border-emerald-400 resize-y"
                      spellCheck={false}
                    />
                  ) : (
                    <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap max-h-60 overflow-y-auto">
                      {result.content_preview}
                    </div>
                  )}
                </div>

                {/* Actions */}
                {!applyDone ? (
                  <div className="flex items-center gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => applyMut.mutate()}
                      disabled={applyMut.isPending}
                      className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 bg-emerald-600 text-white text-xs rounded-lg hover:bg-emerald-700 disabled:opacity-50 cursor-pointer transition-colors"
                    >
                      {applyMut.isPending
                        ? <><RefreshCw size={12} className="animate-spin" /> Publishing draft…</>
                        : <><CheckCircle size={12} /> {editing ? 'Save edits & Publish' : 'Publish as WordPress Draft'}</>}
                    </button>
                    {!editing && (
                      <button
                        type="button"
                        onClick={() => { setResult(null); setKeyword('') }}
                        className="px-3 py-2 border border-slate-200 text-slate-500 text-xs rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
                      >
                        Discard
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <CheckCircle size={14} className="text-emerald-600 shrink-0" />
                    <div>
                      <p className="text-xs font-semibold text-emerald-700">Draft published to WordPress</p>
                      <p className="text-[10px] text-emerald-600 mt-0.5">
                        Find it under Posts → Drafts in your WordPress admin, or view it in the Change Queue history.
                      </p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
