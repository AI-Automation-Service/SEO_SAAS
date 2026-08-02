import { useState, useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Map,
  FileText,
  Layers,
  Globe,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Lock,
  RotateCcw,
  Pencil,
  Save,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { strategyApi, keywordsApi, getErrorMessage } from '@/api/client'
import type { Project } from '@/types/api'
import { cn } from '@/lib/utils'

interface StrategyTabProps {
  projectName: string
  project: Project
}

type SkillKey = 'plan' | 'content' | 'architecture' | 'competitorPage'

// Maps frontend SkillKey → DB strategy_type
const SKILL_TO_DB: Record<SkillKey, string> = {
  plan: 'plan',
  content: 'content',
  architecture: 'architecture',
  competitorPage: 'competitor',
}

// Maps DB strategy_type → frontend SkillKey
const DB_TO_SKILL: Record<string, SkillKey> = {
  plan: 'plan',
  content: 'content',
  architecture: 'architecture',
  competitor: 'competitorPage',
}

function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) {
    return navigator.clipboard.writeText(text)
  }
  return new Promise((resolve) => {
    const el = document.createElement('textarea')
    el.value = text
    el.style.cssText = 'position:fixed;top:-9999px;left:-9999px'
    document.body.appendChild(el)
    el.focus()
    el.select()
    try { document.execCommand('copy') } catch {}
    document.body.removeChild(el)
    resolve()
  })
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={() => {
        copyToClipboard(text).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 2000)
        })
      }}
      className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
    >
      {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

const MD_COMPONENTS: React.ComponentProps<typeof ReactMarkdown>['components'] = {
  h1: ({ children }) => <h1 className="text-base font-bold text-slate-900 mt-5 mb-2">{children}</h1>,
  h2: ({ children }) => <h2 className="text-sm font-bold text-slate-800 mt-4 mb-1.5 border-b border-slate-100 pb-1">{children}</h2>,
  h3: ({ children }) => <h3 className="text-xs font-semibold text-slate-700 mt-3 mb-1">{children}</h3>,
  p: ({ children }) => <p className="text-xs text-slate-600 mb-2 leading-relaxed">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-slate-800">{children}</strong>,
  ul: ({ children }) => <ul className="list-disc list-inside space-y-0.5 mb-2">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside space-y-0.5 mb-2">{children}</ol>,
  li: ({ children }) => <li className="text-xs text-slate-600 leading-relaxed">{children}</li>,
  table: ({ children }) => (
    <div className="overflow-x-auto mb-3">
      <table className="w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-slate-50">{children}</thead>,
  th: ({ children }) => <th className="px-2 py-1.5 text-left font-medium text-slate-600 border border-slate-200 whitespace-nowrap">{children}</th>,
  td: ({ children }) => <td className="px-2 py-1.5 text-slate-600 border border-slate-200">{children}</td>,
  tr: ({ children }) => <tr className="even:bg-slate-50/50">{children}</tr>,
  blockquote: ({ children }) => <blockquote className="border-l-2 border-emerald-300 pl-3 my-2 text-slate-500 text-xs italic">{children}</blockquote>,
  code: ({ children }) => <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px] font-mono text-slate-700">{children}</code>,
  hr: () => <hr className="border-slate-200 my-3" />,
}

interface OutputPanelProps {
  text: string
  expanded: boolean
  onToggle: () => void
  editing: boolean
  editDraft: string
  onEdit: () => void
  onEditChange: (v: string) => void
  onSaveEdit: () => void
  onCancelEdit: () => void
  isSavingEdit: boolean
}

function OutputPanel({
  text, expanded, onToggle,
  editing, editDraft, onEdit, onEditChange, onSaveEdit, onCancelEdit, isSavingEdit,
}: OutputPanelProps) {
  return (
    <div className="mt-3 border border-slate-200 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
        <span className="text-xs font-medium text-slate-500">
          {editing ? 'Editing' : 'Output'}
        </span>
        <div className="flex items-center gap-3">
          {editing ? (
            <>
              <button
                type="button"
                onClick={onSaveEdit}
                disabled={isSavingEdit}
                className="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700 font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                <Save size={11} />
                {isSavingEdit ? 'Saving...' : 'Save'}
              </button>
              <button
                type="button"
                onClick={onCancelEdit}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              >
                <X size={11} />
                Cancel
              </button>
            </>
          ) : (
            <>
              <CopyButton text={text} />
              <button
                type="button"
                onClick={onEdit}
                title="Edit output"
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              >
                <Pencil size={11} />
                Edit
              </button>
              <button
                type="button"
                onClick={onToggle}
                className="text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              >
                {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            </>
          )}
        </div>
      </div>

      {editing ? (
        <textarea
          value={editDraft}
          onChange={(e) => onEditChange(e.target.value)}
          className="w-full h-[500px] p-4 text-xs font-mono text-slate-700 bg-white resize-y focus:outline-none leading-relaxed"
        />
      ) : expanded ? (
        <div className="p-4 max-h-[600px] overflow-y-auto bg-white">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
            {text}
          </ReactMarkdown>
        </div>
      ) : null}
    </div>
  )
}

interface SkillCardProps {
  icon: React.ReactNode
  title: string
  description: string
  text: string | null
  expanded: boolean
  isLoading: boolean
  onGenerate: () => void
  onReset: () => void
  onToggleExpand: () => void
  disabled?: boolean
  // edit
  editing: boolean
  editDraft: string
  onEdit: () => void
  onEditChange: (v: string) => void
  onSaveEdit: () => void
  onCancelEdit: () => void
  isSavingEdit: boolean
}

function SkillCard({
  icon, title, description, text, expanded, isLoading,
  onGenerate, onReset, onToggleExpand, disabled,
  editing, editDraft, onEdit, onEditChange, onSaveEdit, onCancelEdit, isSavingEdit,
}: SkillCardProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0 text-emerald-600">
            {icon}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {text && !isLoading && !editing && (
            <button
              type="button"
              onClick={onReset}
              title="Delete output"
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
            >
              <RotateCcw size={13} />
            </button>
          )}
          {!editing && (
            <button
              type="button"
              onClick={onGenerate}
              disabled={isLoading || disabled}
              className={cn(
                'px-4 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                isLoading
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                  : disabled
                  ? 'bg-slate-100 text-slate-300 cursor-not-allowed'
                  : text
                  ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  : 'bg-emerald-500 text-white hover:bg-emerald-600',
              )}
            >
              {isLoading ? 'Generating...' : text ? 'Regenerate' : 'Generate'}
            </button>
          )}
        </div>
      </div>

      {isLoading && (
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
          <div className="w-3 h-3 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
          Running skill agent — this may take 1–2 minutes...
        </div>
      )}

      {text && (
        <OutputPanel
          text={text}
          expanded={expanded}
          onToggle={onToggleExpand}
          editing={editing}
          editDraft={editDraft}
          onEdit={onEdit}
          onEditChange={onEditChange}
          onSaveEdit={onSaveEdit}
          onCancelEdit={onCancelEdit}
          isSavingEdit={isSavingEdit}
        />
      )}
    </div>
  )
}

export function StrategyTab({ projectName, project }: StrategyTabProps) {
  const qc = useQueryClient()
  const [outputs, setOutputs] = useState<Partial<Record<SkillKey, string>>>({})
  const [expandedKeys, setExpandedKeys] = useState<Set<SkillKey>>(new Set())
  const [editingKey, setEditingKey] = useState<SkillKey | null>(null)
  const [editDraft, setEditDraft] = useState('')
  const [selectedCompetitor, setSelectedCompetitor] = useState('')
  const initialized = useRef(false)

  const { data: summary } = useQuery({
    queryKey: ['keywords-summary', projectName],
    queryFn: () => keywordsApi.summary(projectName),
  })

  // Load persisted outputs on first mount
  const { data: savedOutputs } = useQuery({
    queryKey: ['strategy-saved', projectName],
    queryFn: () => strategyApi.savedOutputs(projectName),
  })

  useEffect(() => {
    if (!savedOutputs || initialized.current) return
    initialized.current = true
    const loaded: Partial<Record<SkillKey, string>> = {}
    const expanded = new Set<SkillKey>()
    for (const [dbType, text] of Object.entries(savedOutputs)) {
      const key = DB_TO_SKILL[dbType]
      if (key && text) {
        loaded[key] = text
        expanded.add(key)
      }
    }
    if (Object.keys(loaded).length > 0) {
      setOutputs(loaded)
      setExpandedKeys(expanded)
    }
  }, [savedOutputs])

  const hasKeywords = (summary?.total ?? 0) > 0
  const hasClusters = (summary?.clusters ?? 0) > 0

  function setOutput(key: SkillKey, text: string) {
    setOutputs((prev) => ({ ...prev, [key]: text }))
    setExpandedKeys((prev) => new Set([...prev, key]))
    setEditingKey(null)
  }

  function toggleExpand(key: SkillKey) {
    setExpandedKeys((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  function startEdit(key: SkillKey) {
    setEditDraft(outputs[key] ?? '')
    setEditingKey(key)
  }

  function cancelEdit() {
    setEditingKey(null)
    setEditDraft('')
  }

  // Delete from DB + clear local state
  const deleteMut = useMutation({
    mutationFn: (key: SkillKey) => strategyApi.deleteOutput(projectName, SKILL_TO_DB[key]),
    onSuccess: (_data, key) => {
      setOutputs((prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      })
      setExpandedKeys((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
      if (editingKey === key) cancelEdit()
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  // Save manual edit to DB
  const editSaveMut = useMutation({
    mutationFn: ({ key, text }: { key: SkillKey; text: string }) =>
      strategyApi.updateOutput(projectName, SKILL_TO_DB[key], text),
    onSuccess: (_data, { key, text }) => {
      setOutputs((prev) => ({ ...prev, [key]: text }))
      cancelEdit()
      toast.success('Output saved')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  // Generation mutations — backend auto-saves; we just update local state
  const planMut = useMutation({
    mutationFn: () => strategyApi.plan(projectName),
    onSuccess: (data) => { setOutput('plan', data.output); qc.invalidateQueries({ queryKey: ['strategy-saved', projectName] }) },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const contentMut = useMutation({
    mutationFn: () => strategyApi.content(projectName),
    onSuccess: (data) => { setOutput('content', data.output); qc.invalidateQueries({ queryKey: ['strategy-saved', projectName] }) },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const archMut = useMutation({
    mutationFn: () => strategyApi.architecture(projectName),
    onSuccess: (data) => { setOutput('architecture', data.output); qc.invalidateQueries({ queryKey: ['strategy-saved', projectName] }) },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const competitorMut = useMutation({
    mutationFn: () => strategyApi.competitorPage(projectName, selectedCompetitor),
    onSuccess: (data) => { setOutput('competitorPage', data.output); qc.invalidateQueries({ queryKey: ['strategy-saved', projectName] }) },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const competitors = project.competitors ?? []

  if (!hasKeywords) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-4">
          <Lock size={20} className="text-slate-400" />
        </div>
        <h3 className="text-sm font-semibold text-slate-700 mb-1">No keywords yet</h3>
        <p className="text-xs text-slate-400 max-w-xs">
          Sync from Google Search Console or upload a CSV in the <strong>Keywords</strong> tab first.
        </p>
      </div>
    )
  }

  if (!hasClusters) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center mb-4">
          <Layers size={20} className="text-amber-400" />
        </div>
        <h3 className="text-sm font-semibold text-slate-700 mb-1">Keywords not clustered yet</h3>
        <p className="text-xs text-slate-400 max-w-xs">
          Go to the <strong>Keywords</strong> tab and click <strong>Run Cluster Agent</strong>. The Strategy tab unlocks once your keywords are grouped into clusters.
        </p>
      </div>
    )
  }

  function skillCardProps(key: SkillKey) {
    return {
      text: outputs[key] ?? null,
      expanded: expandedKeys.has(key),
      onToggleExpand: () => toggleExpand(key),
      onReset: () => deleteMut.mutate(key),
      editing: editingKey === key,
      editDraft: editingKey === key ? editDraft : '',
      onEdit: () => startEdit(key),
      onEditChange: setEditDraft,
      onSaveEdit: () => editSaveMut.mutate({ key, text: editDraft }),
      onCancelEdit: cancelEdit,
      isSavingEdit: editSaveMut.isPending && editingKey === key,
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Strategy Agent</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {summary?.clusters} clusters · {summary?.total} keywords — outputs are saved and persist across sessions
          </p>
        </div>
      </div>

      <SkillCard
        icon={<Map size={16} />}
        title="SEO Plan"
        description="12-month roadmap with 4 phases: Foundation, Expansion, Scale, and Authority. Includes KPI targets and content priorities per cluster."
        isLoading={planMut.isPending}
        onGenerate={() => planMut.mutate()}
        {...skillCardProps('plan')}
      />

      <SkillCard
        icon={<FileText size={16} />}
        title="Content Strategy"
        description="Content pillars, priority topics table, topic cluster map, and publishing cadence — all mapped to your TOFU/MOFU/BOFU funnel."
        isLoading={contentMut.isPending}
        onGenerate={() => contentMut.mutate()}
        {...skillCardProps('content')}
      />

      <SkillCard
        icon={<Layers size={16} />}
        title="Site Architecture"
        description="URL structure, page hierarchy tree, navigation spec, and internal linking plan based on your keyword clusters and suggested URLs."
        isLoading={archMut.isPending}
        onGenerate={() => archMut.mutate()}
        {...skillCardProps('architecture')}
      />

      {/* Competitor Pages */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0 text-emerald-600">
            <Globe size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Competitor Pages</h3>
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
              Generate an SEO-optimized "[Your Brand] vs [Competitor]" comparison page, ready to publish to WordPress.
            </p>
          </div>
        </div>

        {competitors.length === 0 ? (
          <p className="text-xs text-slate-400 bg-slate-50 rounded-lg px-3 py-2.5">
            No competitor URLs configured. Add competitors in your project settings to unlock this feature.
          </p>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {competitors.map((url) => (
                <button
                  key={url}
                  type="button"
                  onClick={() => setSelectedCompetitor(url)}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer',
                    selectedCompetitor === url
                      ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300',
                  )}
                >
                  {url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              {outputs.competitorPage && !competitorMut.isPending && editingKey !== 'competitorPage' && (
                <button
                  type="button"
                  onClick={() => deleteMut.mutate('competitorPage')}
                  title="Delete output"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
                >
                  <RotateCcw size={13} />
                </button>
              )}
              {editingKey !== 'competitorPage' && (
                <button
                  type="button"
                  onClick={() => competitorMut.mutate()}
                  disabled={!selectedCompetitor || competitorMut.isPending}
                  className={cn(
                    'px-4 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                    !selectedCompetitor || competitorMut.isPending
                      ? 'bg-slate-100 text-slate-300 cursor-not-allowed'
                      : outputs.competitorPage
                      ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      : 'bg-emerald-500 text-white hover:bg-emerald-600',
                  )}
                >
                  {competitorMut.isPending
                    ? 'Generating...'
                    : outputs.competitorPage
                    ? 'Regenerate'
                    : 'Generate Comparison Page'}
                </button>
              )}
            </div>

            {competitorMut.isPending && (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <div className="w-3 h-3 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                Running skill agent — this may take 1–2 minutes...
              </div>
            )}

            {outputs.competitorPage && (
              <OutputPanel
                text={outputs.competitorPage}
                expanded={expandedKeys.has('competitorPage')}
                onToggle={() => toggleExpand('competitorPage')}
                {...{
                  editing: editingKey === 'competitorPage',
                  editDraft: editingKey === 'competitorPage' ? editDraft : '',
                  onEdit: () => startEdit('competitorPage'),
                  onEditChange: setEditDraft,
                  onSaveEdit: () => editSaveMut.mutate({ key: 'competitorPage', text: editDraft }),
                  onCancelEdit: cancelEdit,
                  isSavingEdit: editSaveMut.isPending && editingKey === 'competitorPage',
                }}
              />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
