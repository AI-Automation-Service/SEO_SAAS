import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Globe, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react'
import { TopBar } from '@/components/layout/TopBar'
import { StatusBadge } from '@/components/StatusBadge'
import { projectsApi, integrationsApi, getErrorMessage } from '@/api/client'
import type { Project } from '@/types/api'

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: number
  icon: typeof Globe
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-slate-500">{label}</span>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon size={14} />
        </div>
      </div>
      <p className="text-3xl font-semibold font-display text-slate-900">{value}</p>
    </div>
  )
}

function ProjectCard({ project }: { project: Project }) {
  const { data: status } = useQuery({
    queryKey: ['integrations-status', project.name],
    queryFn: () => integrationsApi.status(project.name),
    staleTime: 60_000,
  })

  const allConnected = status?.integrations.every((i) => i.connected) ?? false
  const hasError = status?.integrations.some((i) => !i.connected && i.error && i.error !== 'Not enabled in project.yaml') ?? false

  return (
    <Link
      to={`/projects/${project.name}`}
      className="group bg-white rounded-xl border border-slate-200 p-5 hover:border-emerald-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-slate-900 font-display capitalize">
            {project.name.replace(/-/g, ' ')}
          </h3>
          <p className="text-xs text-slate-400 mt-0.5 uppercase tracking-wide">{project.cms}</p>
        </div>
        <ArrowRight
          size={16}
          className="text-slate-300 group-hover:text-emerald-500 transition-colors mt-1"
        />
      </div>
      <div className="flex items-center gap-2">
        {status ? (
          <StatusBadge
            status={allConnected ? 'connected' : hasError ? 'error' : 'pending'}
            pulse={allConnected}
          />
        ) : (
          <span className="text-xs text-slate-400">Loading...</span>
        )}
      </div>
    </Link>
  )
}

export function DashboardPage() {
  const { data: projects, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  if (isLoading) {
    return (
      <div>
        <TopBar title="Dashboard" subtitle="SEO OS overview" />
        <div className="p-6 flex items-center justify-center h-64 text-slate-400 text-sm">
          Loading projects...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <TopBar title="Dashboard" />
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
            Cannot connect to API — check that the server is running.
            <br />
            <span className="text-red-500 text-xs">{getErrorMessage(error)}</span>
          </div>
        </div>
      </div>
    )
  }

  const total = projects?.length ?? 0

  return (
    <div>
      <TopBar title="Dashboard" subtitle="SEO OS overview" />
      <div className="p-6 space-y-6">
        {/* Metrics */}
        <div className="grid grid-cols-3 gap-4">
          <MetricCard
            label="Total Projects"
            value={total}
            icon={Globe}
            color="bg-slate-100 text-slate-600"
          />
          <MetricCard
            label="Active Integrations"
            value={0}
            icon={CheckCircle2}
            color="bg-emerald-50 text-emerald-600"
          />
          <MetricCard
            label="Needs Attention"
            value={0}
            icon={AlertCircle}
            color="bg-amber-50 text-amber-600"
          />
        </div>

        {/* Projects */}
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3 font-display">
            Projects
          </h2>
          {total === 0 ? (
            <div className="bg-white rounded-xl border border-dashed border-slate-300 p-10 text-center">
              <Globe size={32} className="mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500 text-sm">No projects yet.</p>
              <Link
                to="/projects"
                className="inline-block mt-3 text-emerald-600 text-sm font-medium hover:underline"
              >
                Create your first project →
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {projects?.map((p) => <ProjectCard key={p.name} project={p} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
