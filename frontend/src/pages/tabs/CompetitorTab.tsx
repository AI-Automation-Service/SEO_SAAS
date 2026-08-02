import { useState, useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Globe,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  RotateCcw,
  Pencil,
  Save,
  X,
  Upload,
  ExternalLink,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { strategyApi, getErrorMessage } from '@/api/client'
import { cn } from '@/lib/utils'

interface CompetitorTabProps {
  projectName: string
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    const fn = navigator.clipboard
      ? navigator.clipboard.writeText(text)
      : new Promise<void>((res) => {
          const el = document.createElement('textarea')
          el.value = text
          el.style.cssText = 'position:fixed;top:-9999px;left:-9999px'
          document.body.appendChild(el)
          el.focus(); el.select()
          try { document.execCommand('copy') } catch {}
          document.body.removeChild(el)
          res()
        })
    fn.then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
  }
  return (
    <button
      type="button"
      onClick={copy}
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

interface FaqItem { label: string; text: string }

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

const FAQ: FaqItem[] = [
  {
    label: 'What is a competitor comparison page?',
    text: 'A dedicated page on your website — e.g. yoursite.com/vs/competitor — that compares your product against one competitor. It is a permanent, standalone conversion page, not a blog post.',
  },
  {
    label: 'Why does it matter?',
    text: 'When someone searches "[Your Brand] vs [Competitor]" or "[Competitor] alternative", they are already in buying mode. If you don\'t have a page for that search, a third-party review site ranks there instead and controls what the buyer reads. By publishing your own page, you rank for that keyword and control the narrative.',
  },
  {
    label: 'What the agent produces',
    text: 'A full page in Markdown ready to publish: meta title + description, H1, intro paragraph, feature comparison table (10+ features), pros/cons for each side, a verdict section, 5 FAQ questions optimised for People Also Ask, and a CTA.',
  },
  {
    label: 'One page per competitor',
    text: 'You need one comparison page per competitor you want to target. Each is generated and saved separately — generating for Competitor B never overwrites Competitor A.',
  },
  {
    label: 'What happens after you generate',
    text: 'Review the output, adjust any claims, then click "Publish to WordPress". The system creates a draft PAGE on your WordPress site with the correct slug. You review and publish from WordPress when ready.',
  },
  {
    label: 'Where to link these pages',
    text: 'Link to each comparison page from your Pricing page and Homepage navigation. This signals to Google that the pages are important and gives buyers an easy path during their research.',
  },
  {
    label: 'Which competitor URL to use',
    text: 'Type any competitor\'s homepage URL directly — no pre-configuration needed. The agent uses GPT-4o\'s knowledge of the competitor\'s product to populate the comparison. The "Publish to WordPress" button requires WordPress to be connected in the Integrations tab.',
  },
]

export function CompetitorTab({ projectName }: CompetitorTabProps) {
  const qc = useQueryClient()
  const [competitorOutputs, setCompetitorOutputs] = useState<Record<string, string>>({})
  const [competitorExpanded, setCompetitorExpanded] = useState<Record<string, boolean>>({})
  const [competitorEditingUrl, setCompetitorEditingUrl] = useState<string | null>(null)
  const [competitorEditDraft, setCompetitorEditDraft] = useState('')
  const [publishedUrls, setPublishedUrls] = useState<Record<string, string>>({})
  const [newUrl, setNewUrl] = useState('')
  const initialized = useRef(false)

  const { data: savedOutputs } = useQuery({
    queryKey: ['strategy-saved', projectName],
    queryFn: () => strategyApi.savedOutputs(projectName),
  })

  useEffect(() => {
    if (!savedOutputs || initialized.current) return
    initialized.current = true
    const loaded: Record<string, string> = {}
    const expandedInit: Record<string, boolean> = {}
    for (const [dbType, text] of Object.entries(savedOutputs)) {
      if (dbType.startsWith('competitor:')) {
        const url = dbType.slice('competitor:'.length)
        if (text) { loaded[url] = text; expandedInit[url] = true }
      }
    }
    if (Object.keys(loaded).length > 0) {
      setCompetitorOutputs(loaded)
      setCompetitorExpanded(expandedInit)
    }
  }, [savedOutputs])

  const generateMut = useMutation({
    mutationFn: (url: string) => strategyApi.competitorPage(projectName, url),
    onSuccess: (data, url) => {
      setCompetitorOutputs((prev) => ({ ...prev, [url]: data.output }))
      setCompetitorExpanded((prev) => ({ ...prev, [url]: true }))
      qc.invalidateQueries({ queryKey: ['strategy-saved', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: (url: string) => strategyApi.deleteOutput(projectName, `competitor:${url}`),
    onSuccess: (_data, url) => {
      setCompetitorOutputs((prev) => { const n = { ...prev }; delete n[url]; return n })
      setCompetitorExpanded((prev) => { const n = { ...prev }; delete n[url]; return n })
      if (competitorEditingUrl === url) { setCompetitorEditingUrl(null); setCompetitorEditDraft('') }
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const editSaveMut = useMutation({
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
      toast.success('Draft page created in WordPress — review it before publishing.')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  function submitUrl(raw: string) {
    const url = raw.trim()
    if (!url) return
    setNewUrl('')
    generateMut.mutate(url)
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3 pb-1">
        <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0 text-emerald-600">
          <Globe size={16} />
        </div>
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-slate-900">Competitor Pages</h2>
          <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
            One "[Your Brand] vs [Competitor]" page per competitor — targets high-intent buyers who are already comparing options. Each page is saved separately and can be published to WordPress as a draft.
          </p>
          <AgentFAQ items={FAQ} />
        </div>
      </div>

      {/* URL input */}
      <div className="flex gap-2">
        <input
          type="url"
          value={newUrl}
          onChange={(e) => setNewUrl(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submitUrl(newUrl) }}
          placeholder="https://competitor.com"
          className="flex-1 text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-emerald-400 focus:border-emerald-400"
        />
        <button
          type="button"
          disabled={!newUrl.trim() || generateMut.isPending}
          onClick={() => submitUrl(newUrl)}
          className={cn(
            'px-3 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer shrink-0',
            !newUrl.trim() || generateMut.isPending
              ? 'bg-slate-100 text-slate-300 cursor-not-allowed'
              : 'bg-emerald-500 text-white hover:bg-emerald-600',
          )}
        >
          Generate
        </button>
      </div>

      {/* Generating indicator for new URL (not yet saved) */}
      {generateMut.isPending && generateMut.variables && !competitorOutputs[generateMut.variables] && (
        <div className="flex items-center gap-2 text-xs text-slate-400 px-1">
          <div className="w-3 h-3 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
          Generating page for {generateMut.variables.replace(/^https?:\/\//, '')} — this may take 1–2 minutes...
        </div>
      )}

      {/* Saved competitor output cards */}
      {Object.keys(competitorOutputs).length > 0 && (
        <div className="space-y-4">
          {Object.keys(competitorOutputs).map((url) => {
            const label = url.replace(/^https?:\/\//, '').replace(/\/$/, '')
            const hasOutput = !!competitorOutputs[url]
            const isGenerating = generateMut.isPending && generateMut.variables === url
            const isEditing = competitorEditingUrl === url
            const isPublishing = publishMut.isPending && publishMut.variables === url
            const wpUrl = publishedUrls[url]

            return (
              <div key={url} className="border border-slate-100 rounded-lg p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-medium text-slate-700 truncate">{label}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    {hasOutput && !isGenerating && !isEditing && (
                      <button
                        type="button"
                        onClick={() => deleteMut.mutate(url)}
                        title="Delete output"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
                      >
                        <RotateCcw size={13} />
                      </button>
                    )}
                    {!isEditing && (
                      <button
                        type="button"
                        onClick={() => generateMut.mutate(url)}
                        disabled={isGenerating || generateMut.isPending}
                        className={cn(
                          'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                          isGenerating || generateMut.isPending
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
                                onClick={() => editSaveMut.mutate({ url, text: competitorEditDraft })}
                                disabled={editSaveMut.isPending}
                                className="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700 font-medium transition-colors cursor-pointer disabled:opacity-50"
                              >
                                <Save size={11} />
                                {editSaveMut.isPending ? 'Saving...' : 'Save'}
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

      {/* Empty state */}
      {Object.keys(competitorOutputs).length === 0 && !generateMut.isPending && (
        <div className="text-center py-10 text-xs text-slate-400">
          Enter a competitor URL above and click Generate to create your first comparison page.
        </div>
      )}
    </div>
  )
}
