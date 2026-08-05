import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { Loader2, Lock, Trash2, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { TopBar } from '@/components/layout/TopBar'
import { accountApi, getErrorMessage } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'

const PLAN_COLORS: Record<string, string> = {
  free: 'bg-slate-100 text-slate-600',
  pro: 'bg-blue-100 text-blue-700',
  agency: 'bg-emerald-100 text-emerald-700',
}

const pwSchema = z
  .object({
    current_password: z.string().min(1, 'Required'),
    new_password: z.string().min(8, 'Must be at least 8 characters'),
    confirm_password: z.string().min(1, 'Required'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  })

type PwForm = z.infer<typeof pwSchema>

function SectionCard({ title, icon: Icon, children }: {
  title: string
  icon: typeof Lock
  children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100">
        <Icon size={15} className="text-slate-400" />
        <h2 className="font-display font-semibold text-slate-800 text-sm">{title}</h2>
      </div>
      <div className="px-5 py-4 space-y-4">{children}</div>
    </div>
  )
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      {children}
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  )
}

function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        'w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-white',
        className,
      )}
    />
  )
}

export function AccountPage() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [confirmDelete, setConfirmDelete] = useState('')

  const { data: usage, isLoading } = useQuery({
    queryKey: ['account-usage'],
    queryFn: () => accountApi.usage(),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<PwForm>({
    resolver: zodResolver(pwSchema),
  })

  const pwMut = useMutation({
    mutationFn: (d: PwForm) => accountApi.changePassword(d.current_password, d.new_password),
    onSuccess: () => {
      toast.success('Password changed')
      reset()
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: () => accountApi.deleteAccount(),
    onSuccess: () => {
      toast.success('Account deleted')
      logout()
      navigate('/login')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <div>
      <TopBar title="Account" />
      <div className="p-6 max-w-xl space-y-5">
        {/* Plan info */}
        <SectionCard title="Plan & Usage" icon={User}>
          {isLoading ? (
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <Loader2 size={14} className="animate-spin" /> Loading…
            </div>
          ) : usage ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Email</span>
                <span className="text-sm font-medium text-slate-800">{usage.email}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Plan</span>
                <span className={cn('text-xs font-semibold px-2.5 py-1 rounded-full capitalize', PLAN_COLORS[usage.plan] ?? PLAN_COLORS.free)}>
                  {usage.plan}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Projects</span>
                <span className="text-sm font-medium text-slate-800">
                  {usage.project_count} / {usage.max_projects}
                </span>
              </div>
              {usage.is_admin && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Role</span>
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-purple-100 text-purple-700">Admin</span>
                </div>
              )}
            </div>
          ) : null}
        </SectionCard>

        {/* Change password */}
        <SectionCard title="Change Password" icon={Lock}>
          <form onSubmit={handleSubmit((d) => pwMut.mutate(d))} className="space-y-3">
            <Field label="Current password" error={errors.current_password?.message}>
              <Input type="password" autoComplete="current-password" {...register('current_password')} />
            </Field>
            <Field label="New password" error={errors.new_password?.message}>
              <Input type="password" autoComplete="new-password" {...register('new_password')} />
            </Field>
            <Field label="Confirm new password" error={errors.confirm_password?.message}>
              <Input type="password" autoComplete="new-password" {...register('confirm_password')} />
            </Field>
            <button
              type="submit"
              disabled={pwMut.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {pwMut.isPending && <Loader2 size={14} className="animate-spin" />}
              Change Password
            </button>
          </form>
        </SectionCard>

        {/* Delete account */}
        <SectionCard title="Delete Account" icon={Trash2}>
          <p className="text-sm text-slate-500">
            This permanently deletes your account, all projects, and all data. This cannot be undone.
          </p>
          <Field label={'Type "delete" to confirm'} error={undefined}>
            <Input
              value={confirmDelete}
              onChange={(e) => setConfirmDelete(e.target.value)}
              placeholder="delete"
              autoComplete="off"
            />
          </Field>
          <button
            type="button"
            onClick={() => deleteMut.mutate()}
            disabled={confirmDelete !== 'delete' || deleteMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
          >
            {deleteMut.isPending && <Loader2 size={14} className="animate-spin" />}
            Delete My Account
          </button>
        </SectionCard>
      </div>
    </div>
  )
}
