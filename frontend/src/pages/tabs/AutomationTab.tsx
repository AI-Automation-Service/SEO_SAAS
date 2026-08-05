import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock, Play, ToggleLeft, ToggleRight, Loader2, RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { cronApi, getErrorMessage } from '@/api/client'
import type { CronJob } from '@/types/api'
import { cn } from '@/lib/utils'

const JOB_META: Record<string, { label: string; description: string }> = {
  gsc_sync:         { label: 'GSC Sync',             description: 'Pull fresh keyword data from Google Search Console' },
  ranking_monitor:  { label: 'Ranking Monitor',       description: 'Track position changes for your target keywords' },
  content_refresh:  { label: 'Content Refresh',       description: 'Re-analyse and improve pages that have grown stale' },
  content_calendar: { label: 'Content Calendar',      description: 'Generate article ideas for upcoming content gaps' },
  cluster_improve:  { label: 'Cluster Improvement',   description: 'Run automated page improvements across keyword clusters' },
  meta_audit:       { label: 'Meta Audit',            description: 'Review and fix meta titles/descriptions site-wide' },
}

const DEFAULT_FREQ: Record<string, number> = {
  gsc_sync: 7, ranking_monitor: 7, content_refresh: 30, content_calendar: 7, cluster_improve: 7, meta_audit: 30,
}

const RUN_STATUS_ICON: Record<string, { Icon: typeof CheckCircle; cls: string }> = {
  success:  { Icon: CheckCircle, cls: 'text-emerald-500' },
  failed:   { Icon: XCircle,     cls: 'text-red-500' },
  running:  { Icon: RefreshCw,   cls: 'text-blue-500 animate-spin' },
  skipped:  { Icon: AlertCircle, cls: 'text-slate-400' },
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function FrequencySelect({
  value,
  onChange,
  disabled,
}: {
  value: number
  onChange: (v: number) => void
  disabled?: boolean
}) {
  const options = [1, 3, 7, 14, 30, 60, 90]
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      disabled={disabled}
      className={cn(
        'text-xs border rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-400 transition-colors',
        disabled ? 'bg-slate-50 text-slate-400 border-slate-200 cursor-not-allowed' : 'bg-white text-slate-700 border-slate-300 cursor-pointer',
      )}
    >
      {options.map((d) => (
        <option key={d} value={d}>{d === 1 ? 'Every day' : `Every ${d} days`}</option>
      ))}
    </select>
  )
}

function JobRow({
  projectName,
  jobType,
  job,
}: {
  projectName: string
  jobType: string
  job: CronJob | undefined
}) {
  const qc = useQueryClient()
  const meta = JOB_META[jobType]
  const enabled = job?.enabled ?? false
  const freq = job?.frequency_days ?? DEFAULT_FREQ[jobType]

  const patch = (body: { enabled?: boolean; frequency_days?: number }) =>
    job
      ? cronApi.update(projectName, jobType, body)
      : cronApi.upsert(projectName, { job_type: jobType, frequency_days: freq, enabled: false, ...body })

  const toggleMut = useMutation({
    mutationFn: () => patch({ enabled: !enabled }),
    onSuccess: () => {
      toast.success(enabled ? `${meta.label} disabled` : `${meta.label} enabled`)
      qc.invalidateQueries({ queryKey: ['cron-jobs', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const freqMut = useMutation({
    mutationFn: (days: number) => patch({ frequency_days: days }),
    onSuccess: () => {
      toast.success('Schedule updated')
      qc.invalidateQueries({ queryKey: ['cron-jobs', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const runNowMut = useMutation({
    mutationFn: () => cronApi.runNow(projectName, jobType),
    onSuccess: (data) => {
      toast.success(data.message || `${meta.label} triggered`)
      qc.invalidateQueries({ queryKey: ['cron-runs', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <div className={cn(
      'flex items-start gap-4 px-5 py-4 border-b border-slate-100 last:border-0',
      !enabled && 'opacity-60',
    )}>
      <button
        type="button"
        onClick={() => toggleMut.mutate()}
        disabled={toggleMut.isPending}
        className="mt-0.5 shrink-0 cursor-pointer"
        title={enabled ? 'Disable' : 'Enable'}
      >
        {toggleMut.isPending ? (
          <Loader2 size={22} className="animate-spin text-slate-400" />
        ) : enabled ? (
          <ToggleRight size={22} className="text-emerald-500" />
        ) : (
          <ToggleLeft size={22} className="text-slate-400" />
        )}
      </button>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800">{meta.label}</p>
        <p className="text-xs text-slate-400 mt-0.5">{meta.description}</p>
        {enabled && job?.next_run_at && (
          <p className="text-xs text-slate-400 mt-1">
            Next run: <span className="text-slate-600">{formatDate(job.next_run_at)}</span>
            {job.last_run_at && (
              <> · Last: <span className="text-slate-600">{formatDate(job.last_run_at)}</span></>
            )}
          </p>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <FrequencySelect
          value={freq}
          onChange={(v) => freqMut.mutate(v)}
          disabled={freqMut.isPending}
        />
        <button
          type="button"
          onClick={() => runNowMut.mutate()}
          disabled={!job || runNowMut.isPending}
          title="Run now"
          className="flex items-center gap-1 px-2 py-1.5 text-xs border border-slate-300 text-slate-600 rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
        >
          {runNowMut.isPending ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
          Run
        </button>
      </div>
    </div>
  )
}

function RunHistory({ projectName }: { projectName: string }) {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['cron-runs', projectName],
    queryFn: () => cronApi.runs(projectName),
    refetchInterval: 120_000,
  })

  if (isLoading) return <div className="text-xs text-slate-400 p-4">Loading run history…</div>
  if (runs.length === 0) return <div className="text-xs text-slate-400 p-4">No runs yet — enable a job to get started.</div>

  return (
    <div className="divide-y divide-slate-100">
      {runs.slice(0, 20).map((run) => {
        const s = RUN_STATUS_ICON[run.status] ?? RUN_STATUS_ICON.skipped
        const Icon = s.Icon
        return (
          <div key={run.id} className="flex items-center gap-3 px-5 py-3">
            <Icon size={14} className={s.cls} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-700">{formatDate(run.started_at)}</p>
              {run.error_detail && (
                <p className="text-xs text-red-500 truncate">{run.error_detail}</p>
              )}
            </div>
            <div className="text-xs text-slate-400 text-right shrink-0 space-y-0.5">
              <p>{run.changes_created} changes</p>
              {run.auto_applied > 0 && <p className="text-emerald-600">{run.auto_applied} auto-applied</p>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function AutomationTab({ projectName }: { projectName: string }) {
  const [activeSection, setActiveSection] = useState<'jobs' | 'history'>('jobs')

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ['cron-jobs', projectName],
    queryFn: () => cronApi.list(projectName),
  })

  const jobMap = Object.fromEntries(jobs.map((j) => [j.job_type, j]))

  return (
    <div className="space-y-5 max-w-2xl">
      <div>
        <h2 className="text-base font-semibold text-slate-900">Automation</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Schedule recurring SEO tasks. Enable jobs and set how often they should run.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {(['jobs', 'history'] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setActiveSection(s)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors capitalize',
              activeSection === s
                ? 'border-emerald-500 text-emerald-600'
                : 'border-transparent text-slate-500 hover:text-slate-700',
            )}
          >
            {s === 'jobs' ? 'Scheduled Jobs' : 'Run History'}
          </button>
        ))}
      </div>

      {activeSection === 'jobs' && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="flex items-center gap-2 p-5 text-slate-400 text-sm">
              <Loader2 size={14} className="animate-spin" /> Loading jobs…
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-2 px-5 py-3 border-b border-slate-100 bg-slate-50">
                <Clock size={14} className="text-slate-400" />
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Job</span>
                <span className="ml-auto text-xs font-medium text-slate-500 uppercase tracking-wide">Schedule</span>
              </div>
              {Object.keys(JOB_META).map((jobType) => (
                <JobRow
                  key={jobType}
                  projectName={projectName}
                  jobType={jobType}
                  job={jobMap[jobType]}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeSection === 'history' && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-slate-100 bg-slate-50">
            <RefreshCw size={14} className="text-slate-400" />
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Recent Runs</span>
          </div>
          <RunHistory projectName={projectName} />
        </div>
      )}
    </div>
  )
}
