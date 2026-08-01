import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
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
} from 'lucide-react'
import toast from 'react-hot-toast'
import { strategyApi, keywordsApi, getErrorMessage } from '@/api/client'
import type { Project } from '@/types/api'
import { cn } from '@/lib/utils'

interface StrategyTabProps {
  projectName: string
  project: Project
}

interface SkillOutput {
  text: string
  expanded: boolean
}

type SkillKey = 'plan' | 'content' | 'architecture' | 'competitorPage'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <button
      type="button"
      onClick={handleCopy}
      className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
    >
      {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function OutputPanel({ text, onToggle, expanded }: { text: string; onToggle: () => void; expanded: boolean }) {
  return (
    <div className="mt-3 border border-slate-200 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
        <span className="text-xs font-medium text-slate-500">Output</span>
        <div className="flex items-center gap-3">
          <CopyButton text={text} />
          <button
            type="button"
            onClick={onToggle}
            className="text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>
      {expanded && (
        <pre className="p-4 text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed max-h-[500px] overflow-y-auto bg-white">
          {text}
        </pre>
      )}
    </div>
  )
}

interface SkillCardProps {
  icon: React.ReactNode
  title: string
  description: string
  output: SkillOutput | null
  isLoading: boolean
  onGenerate: () => void
  onReset: () => void
  onToggleExpand: () => void
  disabled?: boolean
}

function SkillCard({
  icon, title, description, output, isLoading, onGenerate, onReset, onToggleExpand, disabled,
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
          {output && !isLoading && (
            <button
              type="button"
              onClick={onReset}
              title="Clear output"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <RotateCcw size={13} />
            </button>
          )}
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
                : output
                ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                : 'bg-emerald-500 text-white hover:bg-emerald-600',
            )}
          >
            {isLoading ? 'Generating...' : output ? 'Regenerate' : 'Generate'}
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
          <div className="w-3 h-3 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
          Running skill agent — this may take 1–2 minutes...
        </div>
      )}

      {output && (
        <OutputPanel
          text={output.text}
          expanded={output.expanded}
          onToggle={onToggleExpand}
        />
      )}
    </div>
  )
}

export function StrategyTab({ projectName, project }: StrategyTabProps) {
  const [outputs, setOutputs] = useState<Partial<Record<SkillKey, SkillOutput>>>({})
  const [selectedCompetitor, setSelectedCompetitor] = useState<string>('')

  const { data: summary } = useQuery({
    queryKey: ['keywords-summary', projectName],
    queryFn: () => keywordsApi.summary(projectName),
  })

  const hasKeywords = (summary?.total ?? 0) > 0
  const hasClusters = (summary?.clusters ?? 0) > 0

  function setOutput(key: SkillKey, text: string) {
    setOutputs((prev) => ({ ...prev, [key]: { text, expanded: true } }))
  }

  function resetOutput(key: SkillKey) {
    setOutputs((prev) => {
      const next = { ...prev }
      delete next[key]
      return next
    })
  }

  function toggleExpand(key: SkillKey) {
    setOutputs((prev) => {
      const curr = prev[key]
      if (!curr) return prev
      return { ...prev, [key]: { ...curr, expanded: !curr.expanded } }
    })
  }

  const planMut = useMutation({
    mutationFn: () => strategyApi.plan(projectName),
    onSuccess: (data) => setOutput('plan', data.output),
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const contentMut = useMutation({
    mutationFn: () => strategyApi.content(projectName),
    onSuccess: (data) => setOutput('content', data.output),
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const archMut = useMutation({
    mutationFn: () => strategyApi.architecture(projectName),
    onSuccess: (data) => setOutput('architecture', data.output),
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const competitorMut = useMutation({
    mutationFn: () => strategyApi.competitorPage(projectName, selectedCompetitor),
    onSuccess: (data) => setOutput('competitorPage', data.output),
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const competitors = project.competitors ?? []

  // ── Locked states ──────────────────────────────────────────────────────────
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

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Strategy Agent</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {summary?.clusters} clusters · {summary?.total} keywords — AI generates strategy based on your keyword data
          </p>
        </div>
      </div>

      {/* Skill cards */}
      <SkillCard
        icon={<Map size={16} />}
        title="SEO Plan"
        description="12-month roadmap with 4 phases: Foundation, Expansion, Scale, and Authority. Includes KPI targets and content priorities per cluster."
        output={outputs.plan ?? null}
        isLoading={planMut.isPending}
        onGenerate={() => planMut.mutate()}
        onReset={() => resetOutput('plan')}
        onToggleExpand={() => toggleExpand('plan')}
      />

      <SkillCard
        icon={<FileText size={16} />}
        title="Content Strategy"
        description="Content pillars, priority topics table, topic cluster map, and publishing cadence — all mapped to your TOFU/MOFU/BOFU funnel."
        output={outputs.content ?? null}
        isLoading={contentMut.isPending}
        onGenerate={() => contentMut.mutate()}
        onReset={() => resetOutput('content')}
        onToggleExpand={() => toggleExpand('content')}
      />

      <SkillCard
        icon={<Layers size={16} />}
        title="Site Architecture"
        description="URL structure, page hierarchy tree, navigation spec, and internal linking plan based on your keyword clusters and suggested URLs."
        output={outputs.architecture ?? null}
        isLoading={archMut.isPending}
        onGenerate={() => archMut.mutate()}
        onReset={() => resetOutput('architecture')}
        onToggleExpand={() => toggleExpand('architecture')}
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
            No competitor URLs configured in this project. Add competitors in your project settings to unlock this feature.
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
              {outputs.competitorPage && !competitorMut.isPending && (
                <button
                  type="button"
                  onClick={() => resetOutput('competitorPage')}
                  title="Clear output"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  <RotateCcw size={13} />
                </button>
              )}
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
            </div>

            {competitorMut.isPending && (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <div className="w-3 h-3 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                Running skill agent — this may take 1–2 minutes...
              </div>
            )}

            {outputs.competitorPage && (
              <OutputPanel
                text={outputs.competitorPage.text}
                expanded={outputs.competitorPage.expanded}
                onToggle={() => toggleExpand('competitorPage')}
              />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
