import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Globe, RefreshCw, Pencil, Check, X, FileSearch } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { projectsApi, integrationsApi, sitemapApi, getErrorMessage } from '@/api/client'
import type { Project } from '@/types/api'
import { cn } from '@/lib/utils'

const INTEGRATION_LABELS: Record<string, string> = {
  wordpress: 'WordPress',
  google_search_console: 'Search Console',
  google_analytics: 'Google Analytics',
}

function WebsiteField({ project }: { project: Project }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(project.website ?? '')

  const { mutate, isPending } = useMutation({
    mutationFn: () => projectsApi.update(project.name, { website: value }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project', project.name] })
      toast.success('Website URL updated')
      setEditing(false)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const cancel = () => {
    setValue(project.website ?? '')
    setEditing(false)
  }

  if (editing) {
    return (
      <div>
        <dt className="text-slate-500 mb-0.5">Website</dt>
        <dd className="flex items-center gap-2 mt-1">
          <input
            autoFocus
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') mutate(); if (e.key === 'Escape') cancel() }}
            className="flex-1 px-2 py-1 border border-emerald-400 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            placeholder="https://yoursite.com"
          />
          <button
            onClick={() => mutate()}
            disabled={isPending || !value.trim()}
            className="p-1.5 rounded-md bg-emerald-500 text-white hover:bg-emerald-600 disabled:opacity-50 transition-colors cursor-pointer"
          >
            <Check size={12} />
          </button>
          <button
            onClick={cancel}
            className="p-1.5 rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors cursor-pointer"
          >
            <X size={12} />
          </button>
        </dd>
      </div>
    )
  }

  return (
    <div>
      <dt className="text-slate-500 mb-0.5">Website</dt>
      <dd className="flex items-center gap-2 font-medium text-slate-900 group">
        {project.website ? (
          <a
            href={project.website}
            target="_blank"
            rel="noreferrer"
            className="text-emerald-600 hover:underline flex items-center gap-1"
          >
            <Globe size={12} />
            {project.website}
          </a>
        ) : (
          <span className="text-slate-400 text-sm italic">Not set</span>
        )}
        <button
          onClick={() => { setValue(project.website ?? ''); setEditing(true) }}
          className={cn(
            'p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer',
            'opacity-0 group-hover:opacity-100'
          )}
          title="Edit website URL"
        >
          <Pencil size={11} />
        </button>
      </dd>
    </div>
  )
}

export function OverviewTab({ project }: { project: Project }) {
  const qc = useQueryClient()

  const { data: status, isLoading, refetch } = useQuery({
    queryKey: ['integrations-status', project.name],
    queryFn: () => integrationsApi.status(project.name),
  })

  const { data: validation } = useQuery({
    queryKey: ['validate', project.name],
    queryFn: () => projectsApi.validate(project.name),
  })

  const { data: sitemapData } = useQuery({
    queryKey: ['sitemap-summary', project.name],
    queryFn: () => sitemapApi.summary(project.name),
  })

  const sitemapMut = useMutation({
    mutationFn: () => sitemapApi.sync(project.name),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['sitemap-summary', project.name] })
      toast.success(data.message)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
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
          <WebsiteField project={project} />
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
            onClick={() => { refetch().catch(() => toast.error('Failed to refresh status')) }}
            className="text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
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
              <div key={item.name} className="border border-slate-100 rounded-lg p-3 text-sm">
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
                  <p className="text-red-500 text-xs mt-1.5 leading-relaxed">{item.error}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Sitemap */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileSearch size={15} className="text-slate-400" />
            <h3 className="font-display font-semibold text-slate-900">Existing Pages</h3>
          </div>
          <button
            type="button"
            onClick={() => sitemapMut.mutate()}
            disabled={sitemapMut.isPending || !project.website}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
              sitemapMut.isPending || !project.website
                ? 'bg-slate-100 text-slate-300 cursor-not-allowed'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
            )}
          >
            {sitemapMut.isPending ? 'Syncing...' : 'Sync Sitemap'}
          </button>
        </div>
        {sitemapData && sitemapData.total > 0 ? (
          <div className="flex items-center gap-4 text-sm">
            <div>
              <span className="text-2xl font-bold text-slate-900">{sitemapData.total}</span>
              <span className="text-slate-500 ml-1.5">pages found</span>
            </div>
            {sitemapData.last_synced && (
              <span className="text-xs text-slate-400">
                Last synced {new Date(sitemapData.last_synced).toLocaleDateString()}
              </span>
            )}
          </div>
        ) : (
          <p className="text-xs text-slate-400 leading-relaxed">
            Sync your sitemap to discover which pages already exist — the system uses this to avoid suggesting new content for topics already covered.
            {!project.website && (
              <span className="block mt-1 text-amber-500">Set your website URL above first.</span>
            )}
          </p>
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
