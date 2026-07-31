import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { Plus, FolderOpen, ArrowRight } from 'lucide-react'
import { TopBar } from '@/components/layout/TopBar'
import { projectsApi, getErrorMessage } from '@/api/client'

const createSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .regex(/^[a-z0-9-]+$/, 'Only lowercase letters, numbers, and hyphens'),
  cms: z.enum(['wordpress', 'shopify'] as const, { error: 'Select a CMS' }),
})
type CreateForm = z.infer<typeof createSchema>

function CreateProjectModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CreateForm>({ resolver: zodResolver(createSchema) })

  const { mutate, isPending } = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      toast.success(`Project "${data.name}" created`)
      navigate(`/projects/${data.name}`)  // backend now returns { name, path, message }
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="font-display font-semibold text-slate-900 text-lg mb-5">
          New Project
        </h2>
        <form onSubmit={handleSubmit((d) => mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Project Name
            </label>
            <input
              {...register('name')}
              placeholder="client-a"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
            {errors.name && (
              <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>
            )}
            <p className="text-slate-400 text-xs mt-1">
              Lowercase letters, numbers, hyphens only
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">CMS</label>
            <select
              {...register('cms')}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
            >
              <option value="">Select CMS...</option>
              <option value="wordpress">WordPress</option>
              <option value="shopify">Shopify</option>
            </select>
            {errors.cms && (
              <p className="text-red-500 text-xs mt-1">{errors.cms.message}</p>
            )}
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex-1 px-4 py-2 text-sm bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-colors font-medium"
            >
              {isPending ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function ProjectsPage() {
  const [showModal, setShowModal] = useState(false)
  const { data: projects, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  return (
    <div>
      <TopBar
        title="Projects"
        subtitle="Manage your client websites"
        action={
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 transition-colors"
          >
            <Plus size={14} />
            New Project
          </button>
        }
      />

      <div className="p-6">
        {isLoading && (
          <div className="text-slate-400 text-sm text-center py-16">
            Loading projects...
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
            Cannot connect to API — check that the server is running.
          </div>
        )}

        {!isLoading && !error && projects?.length === 0 && (
          <div className="bg-white rounded-xl border border-dashed border-slate-300 p-16 text-center">
            <FolderOpen size={40} className="mx-auto text-slate-300 mb-4" />
            <p className="text-slate-500 text-sm mb-4">No projects yet.</p>
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 transition-colors"
            >
              Create your first project
            </button>
          </div>
        )}

        {projects && projects.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Project
                  </th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    CMS
                  </th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {projects.map((p) => (
                  <tr
                    key={p.name}
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => (window.location.href = `/projects/${p.name}`)}
                  >
                    <td className="px-5 py-3.5 font-medium text-slate-900 capitalize">
                      {p.name.replace(/-/g, ' ')}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 uppercase text-xs tracking-wide">
                      {p.cms}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <ArrowRight size={14} className="text-slate-300 ml-auto" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && <CreateProjectModal onClose={() => setShowModal(false)} />}
    </div>
  )
}
