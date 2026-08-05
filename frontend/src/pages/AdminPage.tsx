import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Trash2, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import { Navigate } from 'react-router-dom'
import { TopBar } from '@/components/layout/TopBar'
import { adminApi, getErrorMessage } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import type { AdminUser } from '@/types/api'
import { cn } from '@/lib/utils'

const PLANS = ['free', 'pro', 'agency'] as const

function PlanSelect({ userId, current }: { userId: number; current: string }) {
  const qc = useQueryClient()
  const { mutate, isPending } = useMutation({
    mutationFn: (plan: string) => adminApi.updatePlan(userId, plan),
    onSuccess: () => {
      toast.success('Plan updated')
      qc.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <div className="relative">
      {isPending && <Loader2 size={12} className="absolute right-6 top-2 animate-spin text-slate-400 pointer-events-none" />}
      <select
        value={current}
        onChange={(e) => mutate(e.target.value)}
        disabled={isPending}
        className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-400 cursor-pointer"
      >
        {PLANS.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>
    </div>
  )
}

function DeleteUserButton({ user }: { user: AdminUser }) {
  const qc = useQueryClient()
  const { mutate, isPending } = useMutation({
    mutationFn: () => adminApi.deleteUser(user.id),
    onSuccess: () => {
      toast.success(`Deleted ${user.email}`)
      qc.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <button
      type="button"
      onClick={() => {
        if (window.confirm(`Delete user ${user.email}? This cannot be undone.`)) mutate()
      }}
      disabled={isPending}
      className="flex items-center gap-1 px-2 py-1.5 text-xs border border-red-200 text-red-500 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors cursor-pointer"
    >
      {isPending ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
    </button>
  )
}

export function AdminPage() {
  const { user } = useAuth()
  if (!user?.is_admin) return <Navigate to="/" replace />
  return <AdminPageContent />
}

function AdminPageContent() {
  const { data: users = [], isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminApi.users(),
  })

  const { data: stats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => adminApi.stats(),
  })

  return (
    <div>
      <TopBar title="Admin" />
      <div className="p-6 space-y-5 max-w-4xl">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Total users', value: stats.total_users },
              { label: 'Active users', value: stats.active_users },
              { label: 'Admins', value: stats.admin_users },
            ].map(({ label, value }) => (
              <div key={label} className="bg-white rounded-xl border border-slate-200 px-5 py-4">
                <p className="text-2xl font-bold text-slate-900">{value}</p>
                <p className="text-xs text-slate-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
        )}

        {/* User table */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100 bg-slate-50">
            <Users size={14} className="text-slate-400" />
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Users</span>
          </div>

          {isLoading ? (
            <div className="flex items-center gap-2 p-5 text-slate-400 text-sm">
              <Loader2 size={14} className="animate-spin" /> Loading users…
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="text-left px-5 py-2.5 text-xs font-medium text-slate-500">Email</th>
                    <th className="text-left px-3 py-2.5 text-xs font-medium text-slate-500">Name</th>
                    <th className="text-left px-3 py-2.5 text-xs font-medium text-slate-500">Plan</th>
                    <th className="text-left px-3 py-2.5 text-xs font-medium text-slate-500">Joined</th>
                    <th className="text-left px-3 py-2.5 text-xs font-medium text-slate-500">Status</th>
                    <th className="px-3 py-2.5" />
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                      <td className="px-5 py-3 text-slate-800 font-medium truncate max-w-[200px]">
                        {u.email}
                        {u.is_admin && (
                          <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-600 font-medium">admin</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-slate-600 truncate max-w-[140px]">{u.full_name}</td>
                      <td className="px-3 py-3">
                        <PlanSelect userId={u.id} current={u.plan} />
                      </td>
                      <td className="px-3 py-3 text-slate-400 text-xs whitespace-nowrap">
                        {new Date(u.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                      </td>
                      <td className="px-3 py-3">
                        <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium', u.is_active ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400')}>
                          {u.is_active ? 'active' : 'inactive'}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        {!u.is_admin && <DeleteUserButton user={u} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
