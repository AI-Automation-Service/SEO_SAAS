import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, ExternalLink, Monitor, Smartphone, Key, Check } from 'lucide-react'
import { api, speedApi, getErrorMessage } from '@/api/client'
import { cn } from '@/lib/utils'

type Strategy = 'mobile' | 'desktop'

const METRICS: { key: string; label: string; hint: string }[] = [
  { key: 'fcp', label: 'First Contentful Paint', hint: 'Good < 1.8s' },
  { key: 'lcp', label: 'Largest Contentful Paint', hint: 'Good < 2.5s' },
  { key: 'tbt', label: 'Total Blocking Time', hint: 'Good < 200ms' },
  { key: 'cls', label: 'Cumulative Layout Shift', hint: 'Good < 0.1' },
  { key: 'si',  label: 'Speed Index', hint: 'Good < 3.4s' },
  { key: 'tti', label: 'Time to Interactive', hint: 'Good < 3.8s' },
]

function scoreColor(s: number) {
  if (s >= 90) return 'text-green-600'
  if (s >= 50) return 'text-amber-500'
  return 'text-red-500'
}

function scoreBg(s: number) {
  if (s >= 90) return 'border-green-200 bg-green-50'
  if (s >= 50) return 'border-amber-200 bg-amber-50'
  return 'border-red-200 bg-red-50'
}

function metricColor(score: number | null) {
  if (score === null || score === undefined) return 'text-slate-400'
  if (score >= 0.9) return 'text-green-600'
  if (score >= 0.5) return 'text-amber-500'
  return 'text-red-500'
}

function metricBg(score: number | null) {
  if (score === null || score === undefined) return 'bg-slate-50 border-slate-100'
  if (score >= 0.9) return 'bg-green-50 border-green-100'
  if (score >= 0.5) return 'bg-amber-50 border-amber-100'
  return 'bg-red-50 border-red-100'
}

function SpeedError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const qc = useQueryClient()
  const [apiKey, setApiKey] = useState('')
  const [saved, setSaved] = useState(false)

  const detail = getErrorMessage(error)

  const { mutate: saveKey, isPending } = useMutation({
    mutationFn: () =>
      api.put('/api/keys/google_api_key', { value: apiKey }),
    onSuccess: () => {
      setSaved(true)
      qc.invalidateQueries({ queryKey: ['speed'] })
      setTimeout(() => { setSaved(false); onRetry() }, 800)
    },
  })

  const isRateLimit = detail.toLowerCase().includes('429') || detail.toLowerCase().includes('rate')

  return (
    <div className="space-y-4">
      <div className="bg-red-50 border border-red-200 rounded-xl p-4">
        <p className="text-red-700 text-sm font-medium mb-1">Analysis failed</p>
        <p className="text-red-500 text-xs font-mono break-all">{detail}</p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <Key size={13} className="text-amber-600 shrink-0" />
          <p className="text-amber-800 text-sm font-medium">
            {isRateLimit ? 'Rate limit hit — add your Google API key to continue' : 'Add a Google API key to fix this'}
          </p>
        </div>
        <p className="text-amber-600 text-xs mb-3">
          Create a free key at <span className="font-mono">console.cloud.google.com</span> → APIs & Services → Credentials → Enable "PageSpeed Insights API"
        </p>
        <div className="flex gap-2">
          <input
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="AIza..."
            className="flex-1 px-3 py-1.5 border border-amber-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 bg-white"
          />
          <button
            onClick={() => saveKey()}
            disabled={isPending || !apiKey.trim() || saved}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 disabled:opacity-50 transition-colors cursor-pointer"
          >
            {saved ? <Check size={13} /> : isPending ? <RefreshCw size={13} className="animate-spin" /> : null}
            {saved ? 'Saved!' : 'Save & retry'}
          </button>
        </div>
      </div>
    </div>
  )
}

export function SpeedTab({ projectName, websiteUrl }: { projectName: string; websiteUrl: string }) {
  const [strategy, setStrategy] = useState<Strategy>('mobile')

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['speed', projectName, strategy],
    queryFn: () => speedApi.get(projectName, strategy),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  return (
    <div className="max-w-2xl">
      {/* Header row */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-display font-semibold text-slate-900 text-sm">Page Speed Insights</h3>
          <a
            href={websiteUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-slate-400 hover:text-slate-600 transition-colors truncate block max-w-xs"
          >
            {websiteUrl}
          </a>
        </div>
        <div className="flex items-center gap-2">
          {/* Mobile / Desktop toggle */}
          <div className="flex bg-slate-100 rounded-lg p-0.5">
            <button
              onClick={() => setStrategy('mobile')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
                strategy === 'mobile' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              )}
            >
              <Smartphone size={12} />
              Mobile
            </button>
            <button
              onClick={() => setStrategy('desktop')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
                strategy === 'desktop' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              )}
            >
              <Monitor size={12} />
              Desktop
            </button>
          </div>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            title="Re-run analysis"
            className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw size={13} className={cn('text-slate-500', isFetching && 'animate-spin')} />
          </button>

          <a
            href={`https://pagespeed.web.dev/analysis?url=${encodeURIComponent(websiteUrl)}`}
            target="_blank"
            rel="noopener noreferrer"
            title="Open full report on pagespeed.web.dev"
            className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 transition-colors"
          >
            <ExternalLink size={13} className="text-slate-500" />
          </a>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-400">
          <RefreshCw size={20} className="animate-spin" />
          <span className="text-sm">Running PageSpeed analysis — this takes ~10 seconds…</span>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <SpeedError error={error} onRetry={() => refetch()} />
      )}

      {/* Results */}
      {data && !isLoading && (
        <>
          {/* Score card */}
          <div className={cn('border rounded-xl p-5 mb-4 flex items-center gap-6', scoreBg(data.performance_score))}>
            <div className="text-center shrink-0">
              <div className={cn('text-6xl font-display font-bold leading-none', scoreColor(data.performance_score))}>
                {data.performance_score}
              </div>
              <div className="text-xs text-slate-500 mt-1.5 font-medium">Performance</div>
            </div>
            <div className="flex-1 space-y-1.5">
              <RangeBadge label="Good" range="90–100" cls="bg-green-100 text-green-700" />
              <RangeBadge label="Needs improvement" range="50–89" cls="bg-amber-100 text-amber-700" />
              <RangeBadge label="Poor" range="0–49" cls="bg-red-100 text-red-700" />
            </div>
          </div>

          {/* Metrics grid */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            {METRICS.map(({ key, label, hint }) => {
              const m = data.metrics[key as keyof typeof data.metrics]
              return (
                <div key={key} className={cn('border rounded-xl p-4', metricBg(m?.score ?? null))}>
                  <div className="text-xs text-slate-500 mb-0.5">{label}</div>
                  <div className={cn('text-2xl font-semibold font-display', metricColor(m?.score ?? null))}>
                    {m?.display ?? '—'}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">{hint}</div>
                </div>
              )
            })}
          </div>

          {/* Opportunities */}
          {data.opportunities.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-slate-800 mb-3">Opportunities</h4>
              <div className="space-y-2">
                {data.opportunities.map((op) => (
                  <div key={op.id} className="flex items-center justify-between bg-amber-50 border border-amber-100 rounded-lg px-4 py-2.5">
                    <span className="text-sm text-slate-700">{op.title}</span>
                    <span className="text-xs font-medium text-amber-700 shrink-0 ml-4">{op.display}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Diagnostics */}
          {data.diagnostics.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-slate-800 mb-3">Diagnostics</h4>
              <div className="space-y-2">
                {data.diagnostics.map((d) => (
                  <div key={d.id} className="flex items-center justify-between bg-slate-50 border border-slate-100 rounded-lg px-4 py-2.5">
                    <span className="text-sm text-slate-700">{d.title}</span>
                    <span className="text-xs text-slate-500 shrink-0 ml-4">{d.display}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-slate-400 mt-2 text-center">
            Data from Google PageSpeed Insights · {strategy} · {new Date().toLocaleTimeString()}
          </p>
        </>
      )}
    </div>
  )
}

function RangeBadge({ label, range, cls }: { label: string; range: string; cls: string }) {
  return (
    <div className={cn('flex items-center justify-between rounded-lg px-3 py-1.5 text-xs', cls)}>
      <span className="font-medium">{label}</span>
      <span className="opacity-70">{range}</span>
    </div>
  )
}
