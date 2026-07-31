import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft } from 'lucide-react'
import { TopBar } from '@/components/layout/TopBar'
import { OverviewTab } from './tabs/OverviewTab'
import { IntegrationsTab } from './tabs/IntegrationsTab'
import { KnowledgeTab } from './tabs/KnowledgeTab'
import { KeywordsTab } from './tabs/KeywordsTab'
import { ContentTab } from './tabs/ContentTab'
import { SpeedTab } from './tabs/SpeedTab'
import { projectsApi } from '@/api/client'
import { cn } from '@/lib/utils'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'integrations', label: 'Integrations' },
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'keywords', label: 'Keywords' },
  { id: 'content', label: 'Content' },
  { id: 'speed', label: 'Speed' },
] as const

type TabId = (typeof TABS)[number]['id']

export function ProjectDetailPage() {
  const { name } = useParams<{ name: string }>()
  const [activeTab, setActiveTab] = useState<TabId>('overview')

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
        <Link
          to="/projects"
          className="inline-flex items-center gap-1 text-slate-400 hover:text-slate-600 text-xs py-3 transition-colors"
        >
          <ChevronLeft size={12} />
          All projects
        </Link>
        <div className="flex gap-1 mt-1">
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
        {activeTab === 'knowledge' && <KnowledgeTab />}
        {activeTab === 'keywords' && <KeywordsTab />}
        {activeTab === 'content' && <ContentTab />}
        {activeTab === 'speed' && (
          <SpeedTab projectName={name!} websiteUrl={project.website ?? ''} />
        )}
      </div>
    </div>
  )
}
