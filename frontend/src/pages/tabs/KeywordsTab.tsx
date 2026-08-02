import { useMemo, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Tags, RefreshCw, Upload, Sparkles, Search, X, ExternalLink,
  ChevronUp, ChevronDown, Trash2, Crown, Zap, HelpCircle, RotateCcw, Info,
  Wand2, Copy, Check, ChevronRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { keywordsApi, strategyApi, getErrorMessage } from '@/api/client'
import type { Keyword, KeywordStatus, KeywordType, FunnelStage } from '@/types/api'
import { cn } from '@/lib/utils'

// ── Tooltip ───────────────────────────────────────────────────────────────────

function Tip({ text }: { text: string }) {
  return (
    <span className="relative group/tip inline-flex items-center ml-0.5">
      <HelpCircle size={10} className="text-slate-300 hover:text-slate-500 cursor-help transition-colors shrink-0" />
      <span
        className={cn(
          'pointer-events-none absolute top-full left-1/2 -translate-x-1/2 mt-1.5 z-[100]',
          // whitespace-normal overrides the parent <th> whitespace-nowrap
          'w-56 whitespace-normal break-words',
          'bg-slate-800 text-slate-100 text-[11px] leading-[1.5] rounded-lg px-2.5 py-2 shadow-xl',
          'opacity-0 group-hover/tip:opacity-100 transition-opacity duration-150',
        )}
      >
        {text}
      </span>
    </span>
  )
}

// ── Badge helpers ─────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<KeywordStatus, string> = {
  covered:     'bg-emerald-100 text-emerald-700',
  quick_win:   'bg-amber-100 text-amber-700',
  opportunity: 'bg-blue-100 text-blue-700',
  gap:         'bg-red-100 text-red-600',
  watch:       'bg-slate-100 text-slate-500',
}
const STATUS_LABELS: Record<KeywordStatus, string> = {
  covered:     'Covered',
  quick_win:   'Quick Win',
  opportunity: 'Opportunity',
  gap:         'Gap',
  watch:       'Watch',
}

const TYPE_STYLES: Record<KeywordType, string> = {
  standard:   'bg-slate-100 text-slate-600',
  question:   'bg-purple-100 text-purple-700',
  branded:    'bg-blue-100 text-blue-700',
  competitor: 'bg-orange-100 text-orange-700',
}

const FUNNEL_STYLES: Record<FunnelStage, string> = {
  tofu: 'bg-sky-100 text-sky-700',
  mofu: 'bg-yellow-100 text-yellow-700',
  bofu: 'bg-emerald-100 text-emerald-700',
}

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span className={cn('inline-block px-2 py-0.5 rounded-full text-xs font-medium', className)}>
      {label}
    </span>
  )
}

// ── Summary card ──────────────────────────────────────────────────────────────

function StatCard({
  label, value, color, active, onClick,
}: {
  label: string
  value: number
  color: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex-1 min-w-[120px] rounded-xl border p-4 text-left transition-all cursor-pointer',
        active
          ? 'border-emerald-400 bg-emerald-50 shadow-sm'
          : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm',
      )}
    >
      <p className={cn('text-2xl font-bold font-display', color)}>{value}</p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
    </button>
  )
}

// ── Sort indicator ────────────────────────────────────────────────────────────

function SortIcon({ field, sort, dir }: { field: string; sort: string; dir: 'asc' | 'desc' }) {
  if (sort !== field) return <ChevronUp size={12} className="opacity-20" />
  return dir === 'asc'
    ? <ChevronUp size={12} className="text-emerald-500" />
    : <ChevronDown size={12} className="text-emerald-500" />
}

// ── Position pill ─────────────────────────────────────────────────────────────

function PosBadge({ pos }: { pos: number | null }) {
  if (pos === null) return <span className="text-slate-300">—</span>
  const cls =
    pos <= 3  ? 'text-emerald-600 font-semibold' :
    pos <= 10 ? 'text-amber-600' :
    pos <= 20 ? 'text-blue-600' : 'text-slate-400'
  return <span className={cls}>{pos.toFixed(1)}</span>
}

// ── Competition bar ───────────────────────────────────────────────────────────

function CompBar({ val }: { val: number | null }) {
  if (val === null) return <span className="text-slate-300">—</span>
  const pct = Math.round(val * 100)
  const color = pct >= 67 ? 'bg-red-400' : pct >= 34 ? 'bg-amber-400' : 'bg-emerald-400'
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-14 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500">{pct}</span>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

type SortField = 'keyword' | 'clicks' | 'impressions' | 'position' | 'volume' | 'ctr' | 'cluster'

const DEFAULT_COL_WIDTHS: Record<string, number> = {
  keyword:     280,
  cluster:     140,
  type:         90,
  funnel:       80,
  status:      110,
  volume:       70,
  clicks:       70,
  impressions:  80,
  position:     60,
  ctr:          60,
  competition:  90,
  gap:          55,
  url:         180,
}

export function KeywordsTab({ projectName }: { projectName: string }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  const [showGuide, setShowGuide] = useState(false)

  // Column resize state
  const [colWidths, setColWidths] = useState<Record<string, number>>(DEFAULT_COL_WIDTHS)

  const tableWidth = useMemo(
    () => Object.values(colWidths).reduce((a, b) => a + b, 0) + 32,
    [colWidths],
  )

  function startResize(col: string, e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    const startX = e.clientX
    const startW = colWidths[col]
    const onMove = (me: MouseEvent) => {
      setColWidths((prev) => ({ ...prev, [col]: Math.max(50, startW + me.clientX - startX) }))
    }
    const onUp = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [funnelFilter, setFunnelFilter] = useState<string>('')
  const [clusterFilter, setClusterFilter] = useState<string>('')
  const [search, setSearch] = useState('')

  // Sort
  const [sort, setSort] = useState<SortField>('impressions')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const toggleSort = (field: SortField) => {
    if (sort === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSort(field); setSortDir('desc') }
  }

  // Data
  const { data: summary } = useQuery({
    queryKey: ['keywords-summary', projectName],
    queryFn: () => keywordsApi.summary(projectName),
  })

  const { data: keywords = [], isLoading } = useQuery({
    queryKey: ['keywords', projectName],
    queryFn: () => keywordsApi.list(projectName),
  })

  // Derived clusters for filter dropdown
  const clusterOptions = useMemo(
    () => [...new Set(keywords.map((k) => k.cluster).filter(Boolean) as string[])].sort(),
    [keywords],
  )

  // Client-side filter + sort
  const filtered = useMemo(() => {
    let rows = keywords
    if (statusFilter)  rows = rows.filter((k) => k.status === statusFilter)
    if (typeFilter)    rows = rows.filter((k) => k.keyword_type === typeFilter)
    if (funnelFilter)  rows = rows.filter((k) => k.funnel_stage === funnelFilter)
    if (clusterFilter) rows = rows.filter((k) => k.cluster === clusterFilter)
    if (search) {
      const q = search.toLowerCase()
      rows = rows.filter((k) => k.keyword.includes(q))
    }

    return [...rows].sort((a, b) => {
      const av = a[sort] ?? (sortDir === 'asc' ? Infinity : -Infinity)
      const bv = b[sort] ?? (sortDir === 'asc' ? Infinity : -Infinity)
      if (typeof av === 'string' && typeof bv === 'string')
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
      return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
    })
  }, [keywords, statusFilter, typeFilter, funnelFilter, clusterFilter, search, sort, sortDir])

  const clearFilters = () => {
    setStatusFilter(''); setTypeFilter(''); setFunnelFilter('')
    setClusterFilter(''); setSearch('')
  }
  const hasFilters = statusFilter || typeFilter || funnelFilter || clusterFilter || search

  // Mutations
  const syncMut = useMutation({
    mutationFn: () => keywordsApi.sync(projectName),
    onSuccess: (data) => {
      toast.success(data.message)
      qc.invalidateQueries({ queryKey: ['keywords', projectName] })
      qc.invalidateQueries({ queryKey: ['keywords-summary', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const clusterMut = useMutation({
    mutationFn: () => keywordsApi.cluster(projectName),
    onSuccess: (data) => {
      toast.success(data.message)
      qc.invalidateQueries({ queryKey: ['keywords', projectName] })
      qc.invalidateQueries({ queryKey: ['keywords-summary', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const uploadMut = useMutation({
    mutationFn: (file: File) => keywordsApi.upload(projectName, file),
    onSuccess: (data) => {
      toast.success(data.message)
      qc.invalidateQueries({ queryKey: ['keywords', projectName] })
      qc.invalidateQueries({ queryKey: ['keywords-summary', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => keywordsApi.remove(projectName, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['keywords', projectName] })
      qc.invalidateQueries({ queryKey: ['keywords-summary', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const resetMut = useMutation({
    mutationFn: () => keywordsApi.reset(projectName),
    onSuccess: (data) => {
      toast.success(data.message)
      qc.invalidateQueries({ queryKey: ['keywords', projectName] })
      qc.invalidateQueries({ queryKey: ['keywords-summary', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  function handleReset() {
    if (confirm('Clear all keywords for this project? You can re-sync from GSC or re-upload a CSV after.')) {
      resetMut.mutate()
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) uploadMut.mutate(file)
    e.target.value = ''
  }

  // ── Empty state ─────────────────────────────────────────────────────────────

  if (!isLoading && keywords.length === 0) {
    return (
      <div className="space-y-4">
        <div className="bg-white rounded-xl border border-slate-200 p-10 text-center">
          <Tags size={40} className="mx-auto text-slate-300 mb-4" />
          <h3 className="font-display font-semibold text-slate-700 text-lg mb-1">No keywords yet</h3>
          <p className="text-slate-400 text-sm mb-6 max-w-sm mx-auto">
            Import keywords from Google Search Console to see what you already rank for, or upload a Keyword Planner export to discover new opportunities.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <button
              type="button"
              onClick={() => syncMut.mutate()}
              disabled={syncMut.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 disabled:opacity-50 cursor-pointer transition-colors"
            >
              <RefreshCw size={14} className={syncMut.isPending ? 'animate-spin' : ''} />
              {syncMut.isPending ? 'Syncing...' : 'Sync from GSC'}
            </button>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={uploadMut.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 text-sm rounded-lg hover:bg-slate-50 disabled:opacity-50 cursor-pointer transition-colors"
            >
              <Upload size={14} />
              {uploadMut.isPending ? 'Uploading...' : 'Upload Keyword Planner CSV'}
            </button>
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
          </div>
        </div>
      </div>
    )
  }

  // ── Main layout ─────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Action bar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="font-display font-semibold text-slate-800 text-base">
          Keywords
          {keywords.length > 0 && (
            <span className="ml-2 text-xs font-normal text-slate-400">{keywords.length} total</span>
          )}
        </h2>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => syncMut.mutate()}
            disabled={syncMut.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <RefreshCw size={12} className={syncMut.isPending ? 'animate-spin' : ''} />
            {syncMut.isPending ? 'Syncing…' : 'Sync GSC'}
          </button>

          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploadMut.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <Upload size={12} />
            {uploadMut.isPending ? 'Uploading…' : 'Upload CSV'}
          </button>
          <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />

          <button
            type="button"
            onClick={() => clusterMut.mutate()}
            disabled={clusterMut.isPending || keywords.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <Sparkles size={12} className={clusterMut.isPending ? 'animate-pulse' : ''} />
            {clusterMut.isPending ? 'Clustering…' : 'Run Cluster Agent'}
          </button>

          {keywords.length > 0 && (
            <button
              type="button"
              onClick={handleReset}
              disabled={resetMut.isPending}
              title="Clear all keywords and start fresh"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-red-200 text-red-500 rounded-lg hover:bg-red-50 disabled:opacity-50 cursor-pointer transition-colors"
            >
              <RotateCcw size={12} className={resetMut.isPending ? 'animate-spin' : ''} />
              {resetMut.isPending ? 'Clearing…' : 'Reset'}
            </button>
          )}
        </div>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="flex gap-3 flex-wrap">
          <StatCard label="Total" value={summary.total} color="text-slate-700"
            active={!statusFilter} onClick={clearFilters} />
          <StatCard label="Covered" value={summary.covered} color="text-emerald-600"
            active={statusFilter === 'covered'} onClick={() => setStatusFilter(statusFilter === 'covered' ? '' : 'covered')} />
          <StatCard label="Quick Wins" value={summary.quick_wins} color="text-amber-600"
            active={statusFilter === 'quick_win'} onClick={() => setStatusFilter(statusFilter === 'quick_win' ? '' : 'quick_win')} />
          <StatCard label="Gaps" value={summary.gaps} color="text-red-600"
            active={statusFilter === 'gap'} onClick={() => setStatusFilter(statusFilter === 'gap' ? '' : 'gap')} />
          <StatCard label="Opportunities" value={summary.opportunities} color="text-blue-600"
            active={statusFilter === 'opportunity'} onClick={() => setStatusFilter(statusFilter === 'opportunity' ? '' : 'opportunity')} />
          <StatCard label="Clusters" value={summary.clusters} color="text-violet-600"
            active={false} onClick={() => {}} />
        </div>
      )}

      {/* Status guide */}
      <div>
        <button
          type="button"
          onClick={() => setShowGuide((v) => !v)}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 cursor-pointer transition-colors"
        >
          <Info size={12} />
          {showGuide ? 'Hide status guide' : 'What do these statuses mean?'}
          <ChevronDown size={11} className={cn('transition-transform', showGuide && 'rotate-180')} />
        </button>

        {showGuide && (
          <div className="mt-2 bg-white border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  <th className="px-4 py-2.5 text-left font-medium text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-2.5 text-left font-medium text-slate-500 uppercase tracking-wide">How it's detected</th>
                  <th className="px-4 py-2.5 text-left font-medium text-slate-500 uppercase tracking-wide">What it means</th>
                  <th className="px-4 py-2.5 text-left font-medium text-slate-500 uppercase tracking-wide">Recommended action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {[
                  {
                    badge: 'Covered', cls: 'bg-emerald-100 text-emerald-700',
                    signal: 'Your page ranks in the top 3 on Google and people are clicking it.',
                    meaning: 'This keyword is working. Your page already dominates this topic.',
                    action: 'Maintain — do not rewrite this page. Add internal links from new articles to keep it strong.',
                  },
                  {
                    badge: 'Quick Win', cls: 'bg-amber-100 text-amber-700',
                    signal: 'Your page appears on page 1 of Google (positions 4–10) and is getting some clicks.',
                    meaning: 'You\'re close to the top — a small improvement is enough to reach position 1–3.',
                    action: 'Optimize — improve the title tag, add 2–3 internal links, and refresh the intro paragraph.',
                  },
                  {
                    badge: 'Opportunity', cls: 'bg-blue-100 text-blue-700',
                    signal: 'Google is showing your page in results but it\'s on page 2 or lower (position 11+).',
                    meaning: 'Google knows your page exists and is relevant, but the content isn\'t strong enough to reach page 1 yet.',
                    action: 'Rewrite — expand the content depth, add an FAQ section, and strengthen on-page SEO.',
                  },
                  {
                    badge: 'Gap', cls: 'bg-red-100 text-red-600',
                    signal: 'Google Search Console shows zero impressions — your site never appeared for this keyword.',
                    meaning: 'You have no page targeting this keyword. Google has nothing to rank.',
                    action: 'Create — write new content (pillar page or spoke article) targeting this keyword.',
                  },
                  {
                    badge: 'Watch', cls: 'bg-slate-100 text-slate-500',
                    signal: 'Manually flagged.',
                    meaning: 'Ranking is unstable or the keyword is under review.',
                    action: 'Monitor — check again in 2–4 weeks before deciding on an action.',
                  },
                ].map(({ badge, cls, signal, meaning, action }) => (
                  <tr key={badge} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3">
                      <span className={cn('inline-block px-2 py-0.5 rounded-full text-xs font-medium', cls)}>{badge}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 whitespace-nowrap">{signal}</td>
                    <td className="px-4 py-3 text-slate-600 max-w-[260px]">{meaning}</td>
                    <td className="px-4 py-3 text-slate-700 font-medium max-w-[300px]">{action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Filter bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[180px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search keywords…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />
        </div>

        <Select value={typeFilter} onChange={setTypeFilter}>
          <option value="">All types</option>
          <option value="standard">Standard</option>
          <option value="question">Question</option>
          <option value="branded">Branded</option>
          <option value="competitor">Competitor</option>
        </Select>

        <Select value={funnelFilter} onChange={setFunnelFilter}>
          <option value="">All funnel stages</option>
          <option value="tofu">ToFu</option>
          <option value="mofu">MoFu</option>
          <option value="bofu">BoFu</option>
        </Select>

        {clusterOptions.length > 0 && (
          <Select value={clusterFilter} onChange={setClusterFilter}>
            <option value="">All clusters</option>
            {clusterOptions.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </Select>
        )}

        {hasFilters && (
          <button
            type="button"
            onClick={clearFilters}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-700 border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
          >
            <X size={11} /> Clear
          </button>
        )}

        <span className="ml-auto text-xs text-slate-400 whitespace-nowrap">
          {filtered.length} of {keywords.length}
        </span>
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="text-sm" style={{ tableLayout: 'fixed', width: `${tableWidth}px` }}>
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <Th field="keyword" col="keyword" sort={sort} dir={sortDir} onClick={toggleSort}
                    onResize={startResize} style={{ width: colWidths.keyword }}
                    className="sticky left-0 bg-slate-50 z-10">
                  Keyword
                </Th>
                <Th field="cluster" col="cluster" sort={sort} dir={sortDir} onClick={toggleSort}
                    onResize={startResize} style={{ width: colWidths.cluster }}>
                  Cluster
                  <Tip text="Keywords grouped into a topic by the Cluster Agent. Each cluster has one Hub (pillar page) and multiple Spokes (supporting articles)." />
                </Th>
                <STh col="type" onResize={startResize} style={{ width: colWidths.type }}>
                  Type
                  <Tip text="Standard: regular keyword. Question: starts with how/what/why/etc. Branded: includes your brand name. Competitor: includes a competitor name." />
                </STh>
                <STh col="funnel" onResize={startResize} style={{ width: colWidths.funnel }}>
                  Funnel
                  <Tip text="ToFu (Top of Funnel): user is learning — write educational content. MoFu (Middle): user is comparing options — write reviews/comparisons. BoFu (Bottom): user is ready to buy — write sales/service pages." />
                </STh>
                <STh col="status" onResize={startResize} style={{ width: colWidths.status }}>
                  Status
                  <Tip text="Covered: ranking top 3 — maintain it. Quick Win: ranking 4–10 — small push gets you to top 3. Opportunity: showing in results but below pos 10 — needs stronger content. Gap: not ranking at all — create new content." />
                </STh>
                <Th field="volume" col="volume" sort={sort} dir={sortDir} onClick={toggleSort}
                    onResize={startResize} style={{ width: colWidths.volume }} className="text-right">
                  Vol.
                  <Tip text="Average monthly searches from Google Keyword Planner. Shows how popular this keyword is." />
                </Th>
                <Th field="clicks" col="clicks" sort={sort} dir={sortDir} onClick={toggleSort}
                    onResize={startResize} style={{ width: colWidths.clicks }} className="text-right">
                  Clicks
                  <Tip text="Actual clicks your site received from Google Search for this keyword in the last 90 days (from Google Search Console)." />
                </Th>
                <Th field="impressions" col="impressions" sort={sort} dir={sortDir} onClick={toggleSort}
                    onResize={startResize} style={{ width: colWidths.impressions }} className="text-right">
                  Impr.
                  <Tip text="Impressions: how many times your page appeared in Google search results for this keyword in the last 90 days. High impressions + low clicks = bad title/description." />
                </Th>
                <Th field="position" col="position" sort={sort} dir={sortDir} onClick={toggleSort}
                    onResize={startResize} style={{ width: colWidths.position }} className="text-right">
                  Pos.
                  <Tip text="Average position in Google search results. Position 1 = top of page 1. Below 10 = page 2 or lower." />
                </Th>
                <Th field="ctr" col="ctr" sort={sort} dir={sortDir} onClick={toggleSort}
                    onResize={startResize} style={{ width: colWidths.ctr }} className="text-right">
                  CTR
                  <Tip text="Click-through rate: percentage of people who clicked your result after seeing it. Low CTR means your title or meta description needs improvement." />
                </Th>
                <STh col="competition" onResize={startResize} style={{ width: colWidths.competition }}>
                  Comp.
                  <Tip text="Competition score (0–100) from Google Keyword Planner. Higher = more advertisers bidding = harder to rank organically. Low competition + decent volume = best opportunity." />
                </STh>
                <STh col="gap" onResize={startResize} style={{ width: colWidths.gap }}>
                  Gap
                  <Tip text="Competitor gap: this keyword drives traffic to competitor sites but not to yours. High-priority target." />
                </STh>
                <STh col="url" onResize={startResize} style={{ width: colWidths.url }}>
                  Current URL
                </STh>
                <th className="px-3 py-2.5 w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 14 }).map((_, j) => (
                      <td key={j} className="px-3 py-3">
                        <div className="h-3 bg-slate-100 rounded animate-pulse" style={{ width: `${40 + Math.random() * 50}%` }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={14} className="px-6 py-10 text-center text-slate-400 text-sm">
                    No keywords match the current filters.
                  </td>
                </tr>
              ) : (
                filtered.map((kw) => (
                  <KeywordRow
                    key={kw.id}
                    kw={kw}
                    projectName={projectName}
                    onDelete={() => {
                      if (confirm(`Remove "${kw.keyword}" from this project?`)) {
                        deleteMut.mutate(kw.id)
                      }
                    }}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cluster legend */}
      {clusterOptions.length > 0 && (
        <ClusterLegend keywords={keywords} />
      )}
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Select({
  value, onChange, children,
}: {
  value: string
  onChange: (v: string) => void
  children: React.ReactNode
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white cursor-pointer"
    >
      {children}
    </select>
  )
}

// ── Resize handle ─────────────────────────────────────────────────────────────

function RHandle({ col, onStart }: { col: string; onStart: (col: string, e: React.MouseEvent) => void }) {
  return (
    <span
      className="absolute right-0 inset-y-0 w-2 cursor-col-resize group/rh z-10"
      onMouseDown={(e) => onStart(col, e)}
    >
      <span className="absolute right-0 top-2 bottom-2 w-px bg-slate-200 group-hover/rh:bg-emerald-400 transition-colors" />
    </span>
  )
}

// ── Sortable column header ─────────────────────────────────────────────────────

function Th({
  field, col, sort, dir, onClick, onResize, children, className, style,
}: {
  field: SortField
  col?: string
  sort: string
  dir: 'asc' | 'desc'
  onClick: (f: SortField) => void
  onResize?: (col: string, e: React.MouseEvent) => void
  children: React.ReactNode
  className?: string
  style?: React.CSSProperties
}) {
  return (
    <th
      style={style}
      className={cn(
        'relative px-3 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide cursor-pointer select-none hover:text-slate-700',
        className,
      )}
      onClick={() => onClick(field)}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        <SortIcon field={field} sort={sort} dir={dir} />
      </span>
      {onResize && col && <RHandle col={col} onStart={onResize} />}
    </th>
  )
}

// ── Static (non-sortable) column header ───────────────────────────────────────

function STh({
  col, onResize, children, className, style,
}: {
  col: string
  onResize: (col: string, e: React.MouseEvent) => void
  children: React.ReactNode
  className?: string
  style?: React.CSSProperties
}) {
  return (
    <th
      style={style}
      className={cn(
        'relative px-3 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide whitespace-nowrap',
        className,
      )}
    >
      {children}
      <RHandle col={col} onStart={onResize} />
    </th>
  )
}

function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) return navigator.clipboard.writeText(text)
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

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={() => copyToClipboard(text).then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      })}
      className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
    >
      {copied ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function KeywordRow({
  kw,
  projectName,
  onDelete,
}: {
  kw: Keyword
  projectName: string
  onDelete: () => void
}) {
  const [output, setOutput] = useState<{ text: string; expanded: boolean } | null>(null)

  const improveMut = useMutation({
    mutationFn: () => strategyApi.improvePage(projectName, kw.id),
    onSuccess: (data) => setOutput({ text: data.output, expanded: true }),
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const pageTypeBadge = kw.page_type && kw.page_type !== 'unknown'
    ? kw.page_type
    : null

  return (
    <>
      <tr className="hover:bg-slate-50/50 transition-colors group">
        {/* Keyword */}
        <td className="px-3 py-2.5 sticky left-0 bg-white group-hover:bg-slate-50/50 transition-colors z-10">
          <div className="flex items-center gap-1.5">
            {kw.is_hub && (
              <span title="Hub / Pillar page"><Crown size={11} className="text-amber-500 shrink-0" /></span>
            )}
            {kw.snippet_opportunity && (
              <span title="Featured snippet opportunity"><Zap size={11} className="text-violet-500 shrink-0" /></span>
            )}
            <span className="font-medium text-slate-800 truncate">{kw.keyword}</span>
            {pageTypeBadge && (
              <span className={cn(
                'shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium',
                pageTypeBadge === 'page'
                  ? 'bg-sky-100 text-sky-600'
                  : 'bg-violet-100 text-violet-600',
              )}>
                {pageTypeBadge}
              </span>
            )}
          </div>
        </td>

        {/* Cluster */}
        <td className="px-3 py-2.5 overflow-hidden">
          <span className="text-xs text-slate-500 truncate block">
            {kw.cluster ?? <span className="text-slate-300">—</span>}
          </span>
        </td>

        {/* Type */}
        <td className="px-3 py-2.5">
          <Badge label={kw.keyword_type} className={TYPE_STYLES[kw.keyword_type] ?? 'bg-slate-100 text-slate-600'} />
        </td>

        {/* Funnel */}
        <td className="px-3 py-2.5">
          {kw.funnel_stage ? (
            <Badge label={kw.funnel_stage.toUpperCase()} className={FUNNEL_STYLES[kw.funnel_stage] ?? 'bg-slate-100 text-slate-600'} />
          ) : <span className="text-slate-300">—</span>}
        </td>

        {/* Status */}
        <td className="px-3 py-2.5">
          <Badge
            label={STATUS_LABELS[kw.status as KeywordStatus] ?? kw.status}
            className={STATUS_STYLES[kw.status as KeywordStatus] ?? 'bg-slate-100 text-slate-600'}
          />
        </td>

        {/* Volume */}
        <td className="px-3 py-2.5 text-right text-xs text-slate-600">
          {kw.volume != null ? kw.volume.toLocaleString() : <span className="text-slate-300">—</span>}
        </td>

        {/* Clicks */}
        <td className="px-3 py-2.5 text-right text-xs text-slate-600">
          {kw.clicks != null ? kw.clicks.toLocaleString() : <span className="text-slate-300">—</span>}
        </td>

        {/* Impressions */}
        <td className="px-3 py-2.5 text-right text-xs text-slate-600">
          {kw.impressions != null ? kw.impressions.toLocaleString() : <span className="text-slate-300">—</span>}
        </td>

        {/* Position */}
        <td className="px-3 py-2.5 text-right text-xs">
          <PosBadge pos={kw.position} />
        </td>

        {/* CTR */}
        <td className="px-3 py-2.5 text-right text-xs text-slate-600">
          {kw.ctr != null ? `${(kw.ctr * 100).toFixed(1)}%` : <span className="text-slate-300">—</span>}
        </td>

        {/* Competition */}
        <td className="px-3 py-2.5">
          <CompBar val={kw.competition} />
        </td>

        {/* Competitor gap flag */}
        <td className="px-3 py-2.5 text-center text-xs">
          {kw.competitor_gap ? (
            <span className="text-orange-500" title="Competitor gap">●</span>
          ) : <span className="text-slate-200">●</span>}
        </td>

        {/* Current URL */}
        <td className="px-3 py-2.5 overflow-hidden">
          {kw.existing_url ? (
            <a
              href={kw.existing_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline truncate"
            >
              <ExternalLink size={10} className="shrink-0" />
              <span className="truncate">{kw.existing_url.replace(/^https?:\/\/[^/]+/, '')}</span>
            </a>
          ) : <span className="text-slate-300 text-xs">—</span>}
        </td>

        {/* Actions */}
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {kw.existing_url && (
              <button
                type="button"
                onClick={() => improveMut.mutate()}
                disabled={improveMut.isPending}
                title="Improve this page with AI"
                className={cn(
                  'p-1 rounded text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 transition-all cursor-pointer',
                  improveMut.isPending && 'text-emerald-500 animate-pulse',
                )}
              >
                <Wand2 size={13} />
              </button>
            )}
            <button
              type="button"
              onClick={onDelete}
              className="p-1 rounded text-slate-300 hover:text-red-500 transition-all cursor-pointer"
              title="Remove keyword"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </td>
      </tr>

      {/* Improvement output row */}
      {output && (
        <tr className="bg-emerald-50/40 border-b border-emerald-100">
          <td colSpan={14} className="px-4 py-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Wand2 size={13} className="text-emerald-600" />
                <span className="text-xs font-semibold text-emerald-800">
                  Page Improvement Plan — {kw.keyword}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <CopyBtn text={output.text} />
                <button
                  type="button"
                  onClick={() => setOutput((o) => o ? { ...o, expanded: !o.expanded } : null)}
                  className="text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                >
                  {output.expanded
                    ? <ChevronUp size={13} />
                    : <ChevronRight size={13} />}
                </button>
                <button
                  type="button"
                  onClick={() => setOutput(null)}
                  className="text-slate-300 hover:text-slate-500 transition-colors cursor-pointer"
                  title="Close"
                >
                  <X size={13} />
                </button>
              </div>
            </div>
            {output.expanded && (
              <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed max-h-[400px] overflow-y-auto bg-white border border-emerald-100 rounded-lg p-3">
                {output.text}
              </pre>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

// ── Cluster legend ─────────────────────────────────────────────────────────────

function ClusterLegend({ keywords }: { keywords: Keyword[] }) {
  const clusters = useMemo(() => {
    const map = new Map<string, { hub: string | null; count: number; statuses: string[] }>()
    for (const kw of keywords) {
      if (!kw.cluster) continue
      const entry = map.get(kw.cluster) ?? { hub: null, count: 0, statuses: [] }
      entry.count++
      entry.statuses.push(kw.status)
      if (kw.is_hub) entry.hub = kw.keyword
      map.set(kw.cluster, entry)
    }
    return [...map.entries()].sort((a, b) => b[1].count - a[1].count)
  }, [keywords])

  if (clusters.length === 0) return null

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-slate-700 mb-3">Cluster Overview</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {clusters.map(([name, info]) => {
          const covered = info.statuses.filter((s) => s === 'covered' || s === 'quick_win').length
          const pct = Math.round((covered / info.count) * 100)
          return (
            <div key={name} className="border border-slate-100 rounded-lg p-3">
              <p className="text-xs font-semibold text-slate-700 truncate">{name}</p>
              {info.hub && (
                <p className="text-xs text-amber-600 truncate flex items-center gap-1 mt-0.5">
                  <Crown size={9} /> {info.hub}
                </p>
              )}
              <div className="flex items-center gap-2 mt-2">
                <div className="flex-1 h-1 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-400 rounded-full"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-xs text-slate-400">{info.count} kw</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
