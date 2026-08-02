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
  Upload,
  ExternalLink,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { strategyApi, keywordsApi, getErrorMessage } from '@/api/client'
import type { Project } from '@/types/api'
import { cn } from '@/lib/utils'

interface StrategyTabProps {
  projectName: string
  project: Project
}

type SkillKey = 'plan' | 'content' | 'architecture'

// Maps frontend SkillKey → DB strategy_type
const SKILL_TO_DB: Record<SkillKey, string> = {
  plan: 'plan',
  content: 'content',
  architecture: 'architecture',
}

// Maps DB strategy_type → frontend SkillKey (competitor keys handled separately)
const DB_TO_SKILL: Record<string, SkillKey> = {
  plan: 'plan',
  content: 'content',
  architecture: 'architecture',
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

// ── Agent FAQ accordion ───────────────────────────────────────────────────────

interface FaqItem {
  label: string
  text: string
}

function AgentFAQ({ items }: { items: FaqItem[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-500 transition-colors cursor-pointer"
      >
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
        How does this work?
      </button>
      {open && (
        <div className="mt-2 space-y-2.5 bg-slate-50 border border-slate-100 rounded-lg px-3 py-3">
          {items.map((item) => (
            <div key={item.label}>
              <p className="text-[11px] font-semibold text-slate-600">{item.label}</p>
              <p className="text-[11px] text-slate-500 leading-relaxed mt-0.5">{item.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── FAQ content per agent ─────────────────────────────────────────────────────

const SEO_PLAN_FAQ: FaqItem[] = [
  {
    label: 'What the agent does',
    text: 'Reads your keyword clusters, business context, and goals, then builds a structured 4-phase, 12-month SEO roadmap covering quick wins, content expansion, scaling, and authority building.',
  },
  {
    label: 'What you get',
    text: 'One strategy document with priorities per content pillar, KPI targets per phase, and specific recommendations for technical fixes, content creation, and link-building direction.',
  },
  {
    label: 'When to run it',
    text: 'After your keywords are clustered. Run once to set direction; regenerate whenever you add new keyword clusters or change your business goals.',
  },
  {
    label: 'Note',
    text: 'This is a strategy document — it tells you what to do and in what order. The Content Strategy and Site Architecture agents add the execution detail.',
  },
]

const CONTENT_STRATEGY_FAQ: FaqItem[] = [
  {
    label: 'What the agent does',
    text: 'Takes your keyword clusters and maps them to content pillars, funnel stages (TOFU / MOFU / BOFU), content types, and a recommended publishing cadence.',
  },
  {
    label: 'What "Landing Page", "Hub/Spoke", "Use-Case" means',
    text: 'These are content types the agent recommends you create on your website. The system does not auto-publish pages — you (or your team) build them. A "Landing Page" recommendation means: create a conversion-focused page for that topic.',
  },
  {
    label: 'Why the number of pillars may differ from your cluster count',
    text: 'The agent may merge semantically similar keyword clusters into a single content pillar. 6 keyword clusters might become 4 pillars — this is intentional, not a bug. The agent groups by strategic theme, not just keyword similarity.',
  },
  {
    label: 'When to run it',
    text: 'After the SEO Plan. Use it to decide what content to create and in what order before briefing writers or publishing.',
  },
]

const SITE_ARCHITECTURE_FAQ: FaqItem[] = [
  {
    label: 'What the agent does',
    text: 'Designs your website\'s URL structure, page hierarchy, navigation layout, and internal linking plan — all based on your keyword clusters and any existing pages already on the site.',
  },
  {
    label: 'What you get',
    text: 'A site tree showing every page to create, the URL for each, which section it belongs to, and which pages should link to which.',
  },
  {
    label: 'About internal links',
    text: 'Spoke pages (individual cluster articles) should link back to their Hub (pillar page), and the Hub links to all Spokes. The agent maps this out — you implement the links when creating or editing pages on your site.',
  },
  {
    label: 'When to run it',
    text: 'After Content Strategy. Use it when building a new site or restructuring an existing one to make sure your URL structure supports your SEO goals.',
  },
]

const COMPETITOR_PAGES_FAQ: FaqItem[] = [
  {
    label: 'What is a competitor comparison page?',
    text: 'A dedicated page on your website — for example yoursite.com/vs/competitor — that compares your product or service against one competitor. It is NOT a blog article. It is a permanent, standalone conversion page.',
  },
  {
    label: 'Why does it matter?',
    text: 'When someone searches "[Your Brand] vs [Competitor]" or "[Competitor] alternative", they are already in buying mode — one step away from a decision. If you do not have a page for that search, a third-party review site (G2, Capterra, a blogger) ranks there instead and controls what the buyer reads. By publishing your own comparison page, you rank for that keyword and control the narrative.',
  },
  {
    label: 'What the agent produces',
    text: 'A full page in Markdown ready to publish: meta title + description, H1, intro paragraph, feature comparison table (10+ features), pros/cons for each side, a verdict section, 5 FAQ questions optimised for People Also Ask, and a CTA.',
  },
  {
    label: 'One page per competitor',
    text: 'You need one comparison page for each competitor you want to target. 3 competitors = 3 pages on your WordPress site. Each is generated and saved separately — generating for Competitor B does not overwrite Competitor A.',
  },
  {
    label: 'What happens after you generate',
    text: 'Review the output, adjust any claims you disagree with, then click "Publish to WordPress". The system creates a draft PAGE (not a post) on your WordPress site with the correct title and slug. You review it in WordPress and hit Publish when ready.',
  },
  {
    label: 'Where to link these pages',
    text: 'Link to each comparison page from your Pricing page and Homepage navigation. This tells Google the pages are important and gives buyers an easy path to find them during their research.',
  },
  {
    label: 'Which competitor URL to use',
    text: 'Type any competitor\'s homepage URL directly — no pre-configuration needed. You can also save frequently-used competitors in Project Settings → Competitors to get quick-access buttons here. The "Publish to WordPress" button requires WordPress to be connected in the Integrations tab.',
  },
]

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
  faq: FaqItem[]
  notice?: React.ReactNode
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
  icon, title, description, faq, notice, text, expanded, isLoading,
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
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
            <AgentFAQ items={faq} />
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

      {notice && <div className="mt-3">{notice}</div>}

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
  // Per-competitor state (keyed by competitor URL)
  const [competitorOutputs, setCompetitorOutputs] = useState<Record<string, string>>({})
  const [competitorExpanded, setCompetitorExpanded] = useState<Record<string, boolean>>({})
  const [competitorEditingUrl, setCompetitorEditingUrl] = useState<string | null>(null)
  const [competitorEditDraft, setCompetitorEditDraft] = useState('')
  const [publishedUrls, setPublishedUrls] = useState<Record<string, string>>({})
  const [newCompetitorUrl, setNewCompetitorUrl] = useState('')
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
    const competitorLoaded: Record<string, string> = {}
    const competitorExpandedInit: Record<string, boolean> = {}
    for (const [dbType, text] of Object.entries(savedOutputs)) {
      if (dbType.startsWith('competitor:')) {
        const url = dbType.slice('competitor:'.length)
        if (text) { competitorLoaded[url] = text; competitorExpandedInit[url] = true }
      } else {
        const key = DB_TO_SKILL[dbType]
        if (key && text) { loaded[key] = text; expanded.add(key) }
      }
    }
    if (Object.keys(loaded).length > 0) { setOutputs(loaded); setExpandedKeys(expanded) }
    if (Object.keys(competitorLoaded).length > 0) {
      setCompetitorOutputs(competitorLoaded)
      setCompetitorExpanded(competitorExpandedInit)
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
    mutationFn: (url: string) => strategyApi.competitorPage(projectName, url),
    onSuccess: (data, url) => {
      setCompetitorOutputs((prev) => ({ ...prev, [url]: data.output }))
      setCompetitorExpanded((prev) => ({ ...prev, [url]: true }))
      qc.invalidateQueries({ queryKey: ['strategy-saved', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const competitorDeleteMut = useMutation({
    mutationFn: (url: string) => strategyApi.deleteOutput(projectName, `competitor:${url}`),
    onSuccess: (_data, url) => {
      setCompetitorOutputs((prev) => { const n = { ...prev }; delete n[url]; return n })
      setCompetitorExpanded((prev) => { const n = { ...prev }; delete n[url]; return n })
      if (competitorEditingUrl === url) { setCompetitorEditingUrl(null); setCompetitorEditDraft('') }
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const competitorEditSaveMut = useMutation({
    mutationFn: ({ url, text }: { url: string; text: string }) =>
      strategyApi.updateOutput(projectName, `competitor:${url}`, text),
    onSuccess: (_data, { url, text }) => {
      setCompetitorOutputs((prev) => ({ ...prev, [url]: text }))
      setCompetitorEditingUrl(null)
      setCompetitorEditDraft('')
      toast.success('Output saved')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const publishMut = useMutation({
    mutationFn: (url: string) => strategyApi.publishCompetitor(projectName, url),
    onSuccess: (data, url) => {
      setPublishedUrls((prev) => ({ ...prev, [url]: data.url }))
      toast.success(`Draft page created in WordPress — review it before publishing.`)
    },
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
        faq={SEO_PLAN_FAQ}
        isLoading={planMut.isPending}
        onGenerate={() => planMut.mutate()}
        {...skillCardProps('plan')}
      />

      <SkillCard
        icon={<FileText size={16} />}
        title="Content Strategy"
        description="Content pillars, priority topics table, topic cluster map, and publishing cadence — all mapped to your TOFU/MOFU/BOFU funnel."
        faq={CONTENT_STRATEGY_FAQ}
        notice={
          <div className="flex items-start gap-2 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2.5">
            <span className="text-amber-500 text-xs mt-0.5 shrink-0">ℹ</span>
            <p className="text-[11px] text-amber-700 leading-relaxed">
              <strong>Content types are recommendations, not auto-created pages.</strong>{' '}
              When the output says "Landing Page", "Hub/Spoke", or "Use-Case" — that is the type of page you need to build on your website. The system advises what to create; it does not publish pages automatically.
            </p>
          </div>
        }
        isLoading={contentMut.isPending}
        onGenerate={() => contentMut.mutate()}
        {...skillCardProps('content')}
      />

      <SkillCard
        icon={<Layers size={16} />}
        title="Site Architecture"
        description="URL structure, page hierarchy tree, navigation spec, and internal linking plan based on your keyword clusters and suggested URLs."
        faq={SITE_ARCHITECTURE_FAQ}
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
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-slate-900">Competitor Pages</h3>
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
              One "[Your Brand] vs [Competitor]" page per competitor — targets high-intent buyers who are already comparing options. Each page is saved separately and can be published to WordPress as a draft.
            </p>
            <AgentFAQ items={COMPETITOR_PAGES_FAQ} />
          </div>
        </div>

        {/* URL input to generate for any competitor */}
        <div className="flex gap-2">
          <input
            type="url"
            value={newCompetitorUrl}
            onChange={(e) => setNewCompetitorUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && newCompetitorUrl.trim()) {
                const url = newCompetitorUrl.trim()
                setNewCompetitorUrl('')
                competitorMut.mutate(url)
              }
            }}
            placeholder="https://competitor.com"
            className="flex-1 text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-emerald-400 focus:border-emerald-400"
          />
          <button
            type="button"
            disabled={!newCompetitorUrl.trim() || competitorMut.isPending}
            onClick={() => {
              const url = newCompetitorUrl.trim()
              if (!url) return
              setNewCompetitorUrl('')
              competitorMut.mutate(url)
            }}
            className={cn(
              'px-3 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer shrink-0',
              !newCompetitorUrl.trim() || competitorMut.isPending
                ? 'bg-slate-100 text-slate-300 cursor-not-allowed'
                : 'bg-emerald-500 text-white hover:bg-emerald-600',
            )}
          >
            Generate
          </button>
        </div>

        {/* Pre-configured quick-access buttons */}
        {competitors.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            <span className="text-[11px] text-slate-400 self-center">Quick add:</span>
            {competitors.map((url) => {
              const label = url.replace(/^https?:\/\//, '').replace(/\/$/, '')
              return (
                <button
                  key={url}
                  type="button"
                  onClick={() => setNewCompetitorUrl(url)}
                  className="px-2 py-1 text-[11px] rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors cursor-pointer"
                >
                  {label}
                </button>
              )
            })}
          </div>
        )}

        {/* Competitor output cards — all URLs that have been generated */}
        {Object.keys(competitorOutputs).length > 0 && (
          <div className="space-y-4">
            {Object.keys(competitorOutputs).map((url) => {
              const label = url.replace(/^https?:\/\//, '').replace(/\/$/, '')
              const hasOutput = !!competitorOutputs[url]
              const isGenerating = competitorMut.isPending && competitorMut.variables === url
              const isEditing = competitorEditingUrl === url
              const isPublishing = publishMut.isPending && publishMut.variables === url
              const wpUrl = publishedUrls[url]

              return (
                <div key={url} className="border border-slate-100 rounded-lg p-4">
                  {/* Competitor header row */}
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-medium text-slate-700 truncate">{label}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      {hasOutput && !isGenerating && !isEditing && (
                        <button
                          type="button"
                          onClick={() => competitorDeleteMut.mutate(url)}
                          title="Delete output"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
                        >
                          <RotateCcw size={13} />
                        </button>
                      )}
                      {!isEditing && (
                        <button
                          type="button"
                          onClick={() => competitorMut.mutate(url)}
                          disabled={isGenerating || competitorMut.isPending}
                          className={cn(
                            'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                            isGenerating || competitorMut.isPending
                              ? 'bg-slate-100 text-slate-300 cursor-not-allowed'
                              : hasOutput
                              ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                              : 'bg-emerald-500 text-white hover:bg-emerald-600',
                          )}
                        >
                          {isGenerating ? 'Generating...' : hasOutput ? 'Regenerate' : 'Generate'}
                        </button>
                      )}
                    </div>
                  </div>

                  {isGenerating && (
                    <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
                      <div className="w-3 h-3 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                      Running skill agent — this may take 1–2 minutes...
                    </div>
                  )}

                  {hasOutput && (
                    <>
                      <div className="mt-3 border border-slate-200 rounded-lg overflow-hidden">
                        <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
                          <span className="text-xs font-medium text-slate-500">
                            {isEditing ? 'Editing' : 'Output'}
                          </span>
                          <div className="flex items-center gap-3">
                            {isEditing ? (
                              <>
                                <button
                                  type="button"
                                  onClick={() => competitorEditSaveMut.mutate({ url, text: competitorEditDraft })}
                                  disabled={competitorEditSaveMut.isPending}
                                  className="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700 font-medium transition-colors cursor-pointer disabled:opacity-50"
                                >
                                  <Save size={11} />
                                  {competitorEditSaveMut.isPending ? 'Saving...' : 'Save'}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => { setCompetitorEditingUrl(null); setCompetitorEditDraft('') }}
                                  className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                                >
                                  <X size={11} />
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <CopyButton text={competitorOutputs[url]} />
                                <button
                                  type="button"
                                  onClick={() => { setCompetitorEditingUrl(url); setCompetitorEditDraft(competitorOutputs[url]) }}
                                  className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                                >
                                  <Pencil size={11} />
                                  Edit
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setCompetitorExpanded((prev) => ({ ...prev, [url]: !prev[url] }))}
                                  className="text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                                >
                                  {competitorExpanded[url] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                </button>
                              </>
                            )}
                          </div>
                        </div>

                        {isEditing ? (
                          <textarea
                            value={competitorEditDraft}
                            onChange={(e) => setCompetitorEditDraft(e.target.value)}
                            className="w-full h-[500px] p-4 text-xs font-mono text-slate-700 bg-white resize-y focus:outline-none leading-relaxed"
                          />
                        ) : competitorExpanded[url] ? (
                          <div className="p-4 max-h-[600px] overflow-y-auto bg-white">
                            <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
                              {competitorOutputs[url]}
                            </ReactMarkdown>
                          </div>
                        ) : null}
                      </div>

                      {/* Publish row */}
                      <div className="mt-3 flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => publishMut.mutate(url)}
                          disabled={isPublishing}
                          className={cn(
                            'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                            isPublishing
                              ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                              : 'bg-blue-500 text-white hover:bg-blue-600',
                          )}
                        >
                          <Upload size={11} />
                          {isPublishing ? 'Publishing...' : 'Publish to WordPress'}
                        </button>
                        {wpUrl && (
                          <a
                            href={wpUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                          >
                            <ExternalLink size={11} />
                            View draft
                          </a>
                        )}
                        <span className="text-[11px] text-slate-400">
                          Saved as a draft with the focus keyword as the slug. The full URL follows your WordPress permalink structure.
                        </span>
                      </div>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
