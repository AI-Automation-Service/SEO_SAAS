import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Globe, RefreshCw } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { projectsApi, integrationsApi } from '@/api/client'
import type { Project } from '@/types/api'

const INTEGRATION_LABELS: Record<string, string> = {
  wordpress: 'WordPress',
  google_search_console: 'Search Console',
  google_analytics: 'Google Analytics',
}

export function OverviewTab({ project }: { project: Project }) {
  const { data: status, isLoading, refetch } = useQuery({
    queryKey: ['integrations-status', project.name],
    queryFn: () => integrationsApi.status(project.name),
  })

  const { data: validation } = useQuery({
    queryKey: ['validate', project.name],
    queryFn: () => projectsApi.validate(project.name),
  })

  return (
    <div className="space-y-6">
      {/* Project info */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h3 className="font-display font-semibold text-slate-900 mb-4">Project Info</h3>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-slate-500 mb-0.5">Name</dt>
            <dd className="font-medium text-slate-900 capitalize">
              {project.name.replace(/-/g, ' ')}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 mb-0.5">CMS</dt>
            <dd className="font-medium text-slate-900 uppercase text-xs tracking-wide">
              {project.cms}
            </dd>
          </div>
          {project.url && (
            <div>
              <dt className="text-slate-500 mb-0.5">Website</dt>
              <dd className="font-medium text-slate-900">
                <a
                  href={project.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-emerald-600 hover:underline flex items-center gap-1"
                >
                  <Globe size={12} />
                  {project.url}
                </a>
              </dd>
            </div>
          )}
          {validation && (
            <div>
              <dt className="text-slate-500 mb-0.5">Config</dt>
              <dd>
                <StatusBadge
                  status={validation.valid ? 'connected' : 'error'}
                  label={validation.valid ? 'Valid' : 'Invalid'}
                />
              </dd>
            </div>
          )}
        </dl>
      </div>

      {/* Integration health */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-semibold text-slate-900">Integration Health</h3>
          <button
            onClick={() => {
              refetch().catch(() => toast.error('Failed to refresh status'))
            }}
            className="text-slate-400 hover:text-slate-600 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>

        {isLoading && (
          <p className="text-slate-400 text-sm">Checking integrations...</p>
        )}

        {status && (
          <div className="grid grid-cols-3 gap-3">
            {status.integrations.map((item) => (
              <div
                key={item.name}
                className="border border-slate-100 rounded-lg p-3 text-sm"
              >
                <p className="text-slate-500 text-xs mb-2">
                  {INTEGRATION_LABELS[item.name] ?? item.name}
                </p>
                <StatusBadge
                  status={
                    item.connected
                      ? 'connected'
                      : item.error === 'Not enabled in project.yaml'
                      ? 'pending'
                      : 'error'
                  }
                  pulse={item.connected}
                />
                {item.error && item.error !== 'Not enabled in project.yaml' && (
                  <p className="text-red-500 text-xs mt-1.5 leading-relaxed">
                    {item.error}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Config errors */}
      {validation && !validation.valid && validation.errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-red-700 font-medium text-sm mb-2">Config Issues</p>
          <ul className="text-red-600 text-xs space-y-1 list-disc list-inside">
            {validation.errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
