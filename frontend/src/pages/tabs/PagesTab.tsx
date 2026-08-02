import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, ExternalLink, FileText, Globe } from 'lucide-react'
import toast from 'react-hot-toast'
import { sitemapApi, getErrorMessage } from '@/api/client'
import { cn } from '@/lib/utils'

interface PagesTabProps {
  projectName: string
}

type Filter = 'all' | 'page' | 'post'

export function PagesTab({ projectName }: PagesTabProps) {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<Filter>('all')
  const [search, setSearch] = useState('')

  const { data: pages = [], isLoading } = useQuery({
    queryKey: ['sitemap-pages', projectName],
    queryFn: () => sitemapApi.pages(projectName),
  })

  const syncMut = useMutation({
    mutationFn: () => sitemapApi.sync(projectName),
    onSuccess: (data) => {
      toast.success(data.message)
      qc.invalidateQueries({ queryKey: ['sitemap-pages', projectName] })
      qc.invalidateQueries({ queryKey: ['sitemap-summary', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const filtered = pages.filter((p) => {
    if (filter !== 'all' && p.page_type !== filter) return false
    if (search && !p.slug.toLowerCase().includes(search.toLowerCase()) && !p.url.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const pageCount = pages.filter((p) => p.page_type === 'page').length
  const postCount = pages.filter((p) => p.page_type === 'post').length

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Site Pages</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            All pages and posts extracted from your sitemap — each slug is the keyword for that page.
          </p>
        </div>
        <button
          type="button"
          onClick={() => syncMut.mutate()}
          disabled={syncMut.isPending}
          className={cn(
            'flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer',
            syncMut.isPending
              ? 'bg-slate-100 text-slate-300 cursor-not-allowed'
              : 'bg-emerald-500 text-white hover:bg-emerald-600',
          )}
        >
          <RefreshCw size={12} className={syncMut.isPending ? 'animate-spin' : ''} />
          {syncMut.isPending ? 'Syncing...' : 'Sync Sitemap'}
        </button>
      </div>

      {/* Stats row */}
      {pages.length > 0 && (
        <div className="flex gap-3">
          {[
            { label: 'Total', count: pages.length, id: 'all' as Filter },
            { label: 'Pages', count: pageCount, id: 'page' as Filter },
            { label: 'Posts', count: postCount, id: 'post' as Filter },
          ].map(({ label, count, id }) => (
            <button
              key={id}
              type="button"
              onClick={() => setFilter(id)}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition-colors cursor-pointer',
                filter === id
                  ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                  : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50',
              )}
            >
              {id === 'page' ? <FileText size={12} /> : id === 'post' ? <Globe size={12} /> : null}
              {label}
              <span className={cn(
                'px-1.5 py-0.5 rounded-full text-[10px] font-semibold',
                filter === id ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-500',
              )}>
                {count}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Search */}
      {pages.length > 0 && (
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by slug or URL..."
          className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-emerald-400 focus:border-emerald-400"
        />
      )}

      {/* Empty / loading states */}
      {isLoading && (
        <div className="text-center py-12 text-xs text-slate-400">Loading pages...</div>
      )}

      {!isLoading && pages.length === 0 && (
        <div className="text-center py-12">
          <p className="text-sm font-medium text-slate-600 mb-1">No pages synced yet</p>
          <p className="text-xs text-slate-400">Click "Sync Sitemap" to extract all pages and posts from your WordPress site.</p>
        </div>
      )}

      {/* Table */}
      {filtered.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-4 py-2.5 text-left font-medium text-slate-500 w-20">Type</th>
                <th className="px-4 py-2.5 text-left font-medium text-slate-500">Slug / Keyword</th>
                <th className="px-4 py-2.5 text-left font-medium text-slate-500">URL</th>
                <th className="px-4 py-2.5 text-left font-medium text-slate-500 w-32">Last Synced</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((page) => {
                const slug = page.slug.split('/').filter(Boolean).pop() ?? page.slug
                const keyword = slug.replace(/[-_]+/g, ' ').replace(/\.\w+$/, '')
                const typeLabel = page.page_type === 'page' ? 'Page' : page.page_type === 'post' ? 'Post' : 'Page'
                const typeStyle = page.page_type === 'post'
                  ? 'bg-orange-50 text-orange-600'
                  : 'bg-blue-50 text-blue-600'
                const TypeIcon = page.page_type === 'post' ? Globe : FileText
                return (
                  <tr key={page.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-2.5">
                      <span className={cn(
                        'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium',
                        typeStyle,
                      )}>
                        <TypeIcon size={9} />
                        {typeLabel}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="font-medium text-slate-800">{keyword}</span>
                      <span className="ml-2 text-slate-400 font-mono">{slug}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <a
                        href={page.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-blue-600 hover:underline truncate max-w-xs"
                      >
                        {page.url}
                        <ExternalLink size={10} className="shrink-0" />
                      </a>
                    </td>
                    <td className="px-4 py-2.5 text-slate-400">
                      {new Date(page.synced_at).toLocaleDateString()}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {!isLoading && pages.length > 0 && filtered.length === 0 && (
        <div className="text-center py-8 text-xs text-slate-400">No results match your filter.</div>
      )}
    </div>
  )
}
