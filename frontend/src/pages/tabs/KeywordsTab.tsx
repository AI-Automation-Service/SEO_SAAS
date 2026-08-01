import { useMemo, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Tags, RefreshCw, Upload, Sparkles, Search, X, ExternalLink,
  ChevronUp, ChevronDown, Trash2, Crown, Zap,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { keywordsApi, getErrorMessage } from '@/api/client'
import type { Keyword, KeywordStatus, KeywordType, FunnelStage } from '@/types/api'
import { cn } from '@/lib/utils'

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

export function KeywordsTab({ projectName }: { projectName: string }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

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
          <table className="w-full text-sm min-w-[900px]">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <Th field="keyword" sort={sort} dir={sortDir} onClick={toggleSort} className="min-w-[180px] sticky left-0 bg-slate-50 z-10">Keyword</Th>
                <Th field="cluster" sort={sort} dir={sortDir} onClick={toggleSort}>Cluster</Th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Type</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Funnel</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Status</th>
                <Th field="volume" sort={sort} dir={sortDir} onClick={toggleSort} className="text-right">Vol.</Th>
                <Th field="clicks" sort={sort} dir={sortDir} onClick={toggleSort} className="text-right">Clicks</Th>
                <Th field="impressions" sort={sort} dir={sortDir} onClick={toggleSort} className="text-right">Impr.</Th>
                <Th field="position" sort={sort} dir={sortDir} onClick={toggleSort} className="text-right">Pos.</Th>
                <Th field="ctr" sort={sort} dir={sortDir} onClick={toggleSort} className="text-right">CTR</Th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Comp.</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide w-8">✦</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Current URL</th>
                <th className="px-3 py-2.5" />
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

function Th({
  field, sort, dir, onClick, children, className,
}: {
  field: SortField
  sort: string
  dir: 'asc' | 'desc'
  onClick: (f: SortField) => void
  children: React.ReactNode
  className?: string
}) {
  return (
    <th
      className={cn(
        'px-3 py-2.5 text-left text-xs font-medium text-slate-500 uppercase tracking-wide cursor-pointer select-none hover:text-slate-700',
        className,
      )}
      onClick={() => onClick(field)}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        <SortIcon field={field} sort={sort} dir={dir} />
      </span>
    </th>
  )
}

function KeywordRow({ kw, onDelete }: { kw: Keyword; onDelete: () => void }) {
  return (
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
          <span className="font-medium text-slate-800 truncate max-w-[200px]">{kw.keyword}</span>
        </div>
      </td>

      {/* Cluster */}
      <td className="px-3 py-2.5 max-w-[140px]">
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
      <td className="px-3 py-2.5 max-w-[160px]">
        {kw.existing_url ? (
          <a
            href={kw.existing_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline truncate max-w-[150px]"
          >
            <ExternalLink size={10} className="shrink-0" />
            <span className="truncate">{kw.existing_url.replace(/^https?:\/\/[^/]+/, '')}</span>
          </a>
        ) : <span className="text-slate-300 text-xs">—</span>}
      </td>

      {/* Delete */}
      <td className="px-3 py-2.5">
        <button
          type="button"
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-300 hover:text-red-500 transition-all cursor-pointer"
          title="Remove keyword"
        >
          <Trash2 size={13} />
        </button>
      </td>
    </tr>
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
