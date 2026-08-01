import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { TopBar } from '@/components/layout/TopBar'
import { OverviewTab } from './tabs/OverviewTab'
import { IntegrationsTab } from './tabs/IntegrationsTab'
import { KnowledgeTab } from './tabs/KnowledgeTab'
import { KeywordsTab } from './tabs/KeywordsTab'
import { StrategyTab } from './tabs/StrategyTab'
import { ContentTab } from './tabs/ContentTab'
import { SpeedTab } from './tabs/SpeedTab'
import { projectsApi, getErrorMessage } from '@/api/client'
import { cn } from '@/lib/utils'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'integrations', label: 'Integrations' },
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'keywords', label: 'Keywords' },
  { id: 'strategy', label: 'Strategy' },
  { id: 'content', label: 'Content' },
  { id: 'speed', label: 'Speed' },
] as const

type TabId = (typeof TABS)[number]['id']

function DeleteModal({ projectName, onClose }: { projectName: string; onClose: () => void }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [confirm, setConfirm] = useState('')

  const { mutate, isPending } = useMutation({
    mutationFn: () => projectsApi.delete(projectName),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      toast.success(`Project "${projectName}" deleted`)
      navigate('/projects')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full bg-red-100 flex items-center justify-center shrink-0">
            <Trash2 size={16} className="text-red-600" />
          </div>
          <div>
            <h2 className="font-display font-semibold text-slate-900">Delete project</h2>
            <p className="text-xs text-slate-400">This action cannot be undone</p>
          </div>
        </div>

        <p className="text-sm text-slate-600 mb-4">
          This will permanently delete <strong className="text-slate-900">{projectName}</strong> and all its data — integrations, credentials, content, and settings.
        </p>

        <div className="mb-4">
          <label className="block text-xs font-medium text-slate-700 mb-1.5">
            Type <span className="font-mono bg-slate-100 px-1 rounded">{projectName}</span> to confirm
          </label>
          <input
            type="text"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder={projectName}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
            autoComplete="off"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2 text-sm border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => mutate()}
            disabled={confirm !== projectName || isPending}
            className="flex-1 px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium cursor-pointer"
          >
            {isPending ? 'Deleting...' : 'Delete project'}
          </button>
        </div>
      </div>
    </div>
  )
}

export function ProjectDetailPage() {
  const { name } = useParams<{ name: string }>()
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [showDelete, setShowDelete] = useState(false)

  const { data: project, isLoading, error } = useQuery({
    queryKey: ['project', name],
    queryFn: () => projectsApi.get(name!),
    enabled: !!name,
  })

  if (isLoading) {
    return (
      <div>
        <TopBar title="Project" />
        <div className="p-6 text-slate-400 text-sm">Loading project...</div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div>
        <TopBar title="Project" />
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
            Project not found or server error.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <TopBar
        title={project.name.replace(/-/g, ' ')}
        subtitle={project.cms.toUpperCase()}
      />

      {/* Tab bar */}
      <div className="bg-white border-b border-slate-200 px-6">
        <div className="flex items-center justify-between">
          <Link
            to="/projects"
            className="inline-flex items-center gap-1 text-slate-400 hover:text-slate-600 text-xs py-3 transition-colors"
          >
            <ChevronLeft size={12} />
            All projects
          </Link>
          <button
            type="button"
            onClick={() => setShowDelete(true)}
            className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 transition-colors cursor-pointer py-3"
          >
            <Trash2 size={12} />
            Delete project
          </button>
        </div>
        <div className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-emerald-500 text-emerald-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="p-6">
        {activeTab === 'overview' && <OverviewTab project={project} />}
        {activeTab === 'integrations' && <IntegrationsTab projectName={name!} />}
        {activeTab === 'knowledge' && <KnowledgeTab projectName={name!} />}
        {activeTab === 'keywords' && <KeywordsTab projectName={name!} />}
        {activeTab === 'strategy' && <StrategyTab projectName={name!} project={project} />}
        {activeTab === 'content' && <ContentTab />}
        {activeTab === 'speed' && (
          <SpeedTab projectName={name!} websiteUrl={project.website ?? ''} />
        )}
      </div>

      {showDelete && (
        <DeleteModal projectName={name!} onClose={() => setShowDelete(false)} />
      )}
    </div>
  )
}
