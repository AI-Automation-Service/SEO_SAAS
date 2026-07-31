import { forwardRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { ChevronDown, ChevronUp, Loader2, Pencil, X } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { integrationsApi, getErrorMessage } from '@/api/client'
import type { IntegrationStatusItem } from '@/types/api'
import { cn } from '@/lib/utils'

// ── Shared UI ────────────────────────────────────────────────────────────────

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      {children}
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  )
}

const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, disabled, ...props }, ref) => (
    <input
      ref={ref}
      disabled={disabled}
      {...props}
      className={cn(
        'w-full px-3 py-2 border rounded-lg text-sm focus:outline-none transition-colors',
        disabled
          ? 'border-slate-200 bg-slate-50 text-slate-400 cursor-not-allowed select-none'
          : 'border-slate-300 bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
        className
      )}
    />
  )
)
Input.displayName = 'Input'

const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ disabled, ...props }, ref) => (
    <textarea
      ref={ref}
      disabled={disabled}
      {...props}
      className={cn(
        'w-full px-3 py-2 border rounded-lg text-sm focus:outline-none resize-none font-mono text-xs transition-colors',
        disabled
          ? 'border-slate-200 bg-slate-50 text-slate-400 cursor-not-allowed select-none'
          : 'border-slate-300 bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent'
      )}
    />
  )
)
Textarea.displayName = 'Textarea'

function SaveButton({ loading, label = 'Save & Test' }: { loading: boolean; label?: string }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-colors"
    >
      {loading && <Loader2 size={14} className="animate-spin" />}
      {label}
    </button>
  )
}

function SectionWrapper({
  title,
  status,
  children,
}: {
  title: string
  status?: IntegrationStatusItem
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(true)
  const badgeStatus = status?.connected
    ? 'connected'
    : status?.error === 'Not enabled in project.yaml'
    ? 'pending'
    : status
    ? 'error'
    : 'pending'

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="font-display font-semibold text-slate-900">{title}</span>
          <StatusBadge status={badgeStatus} pulse={status?.connected} />
        </div>
        {open ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 space-y-4">
          {status?.error && status.error !== 'Not enabled in project.yaml' && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-red-600 text-xs">
              {status.error}
            </div>
          )}
          {children}
        </div>
      )}
    </div>
  )
}

// ── WordPress ─────────────────────────────────────────────────────────────────

const wpSchema = z.object({
  url: z.string().url('Must be a valid URL'),
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'App password is required'),
})
type WpForm = z.infer<typeof wpSchema>

function WordPressSection({
  projectName,
  status,
}: {
  projectName: string
  status?: IntegrationStatusItem
}) {
  const isConnected = status?.connected === true
  const [isEditing, setIsEditing] = useState(false)
  const locked = isConnected && !isEditing

  const qc = useQueryClient()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<WpForm>({
    resolver: zodResolver(wpSchema),
  })

  const { mutate, isPending } = useMutation({
    mutationFn: async (data: WpForm) => {
      const envKey = projectName.toUpperCase().replace(/-/g, '_')
      await integrationsApi.updateConfig(projectName, {
        wordpress: {
          enabled: true,
          url: data.url,
          username_env: `WP_${envKey}_USERNAME`,
          password_env: `WP_${envKey}_APP_PASSWORD`,
        },
      })
      await integrationsApi.setSecret(projectName, {
        key: `WP_${envKey}_USERNAME`,
        value: data.username,
      })
      await integrationsApi.setSecret(projectName, {
        key: `WP_${envKey}_APP_PASSWORD`,
        value: data.password,
      })
      return integrationsApi.test(projectName, 'wordpress')
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['integrations-status', projectName] })
      if (result.connected) {
        toast.success('WordPress connected successfully')
        setIsEditing(false)
        reset()
      } else {
        toast.error(`WordPress error: ${result.error}`)
      }
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <SectionWrapper title="WordPress" status={status}>
      <form onSubmit={handleSubmit((d) => mutate(d))} className="space-y-4">
        <Field label="Site URL" error={errors.url?.message}>
          <Input
            {...register('url')}
            placeholder="https://example.com"
            disabled={locked}
          />
        </Field>
        <Field label="Username" error={errors.username?.message}>
          <Input
            {...register('username')}
            placeholder={locked ? '••••••••' : 'admin'}
            autoComplete="off"
            disabled={locked}
          />
        </Field>
        <Field label="Application Password" error={errors.password?.message}>
          <Input
            {...register('password')}
            type="password"
            placeholder={locked ? '••••••••••••••••' : 'xxxx xxxx xxxx xxxx'}
            autoComplete="new-password"
            disabled={locked}
          />
          {!locked && (
            <p className="text-slate-400 text-xs mt-1">
              Generate in WordPress → Users → Profile → Application Passwords
            </p>
          )}
        </Field>

        <div className="flex items-center gap-3">
          {locked ? (
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
            >
              <Pencil size={13} />
              Edit credentials
            </button>
          ) : (
            <>
              <SaveButton loading={isPending} />
              {isConnected && (
                <button
                  type="button"
                  onClick={() => { setIsEditing(false); reset() }}
                  className="flex items-center gap-2 px-4 py-2 text-slate-500 text-sm font-medium rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  <X size={13} />
                  Cancel
                </button>
              )}
            </>
          )}
        </div>
      </form>
    </SectionWrapper>
  )
}

// ── Google ────────────────────────────────────────────────────────────────────

const googleSchema = z.object({
  gsc_site_url: z.string().url('Must be a valid URL'),
  ga4_property_id: z.string().optional(),
  credentials_json: z.string().min(10, 'Paste the full service account JSON'),
})
type GoogleForm = z.infer<typeof googleSchema>

function GoogleSection({
  projectName,
  gscStatus,
  ga4Status,
}: {
  projectName: string
  gscStatus?: IntegrationStatusItem
  ga4Status?: IntegrationStatusItem
}) {
  const isConnected = gscStatus?.connected === true
  const [isEditing, setIsEditing] = useState(false)
  const locked = isConnected && !isEditing

  const qc = useQueryClient()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<GoogleForm>({
    resolver: zodResolver(googleSchema),
  })

  const { mutate, isPending } = useMutation({
    mutationFn: async (data: GoogleForm) => {
      try {
        const parsed = JSON.parse(data.credentials_json)
        if (parsed.type !== 'service_account') {
          throw new Error('Expected a Google service account JSON (type: service_account)')
        }
      } catch (e) {
        throw new Error(e instanceof Error ? e.message : 'Invalid JSON')
      }

      await integrationsApi.updateConfig(projectName, {
        google: {
          enabled: true,
          gsc_site_url: data.gsc_site_url,
          ga4_property_id: data.ga4_property_id || '',
        },
      })
      await integrationsApi.uploadGoogleCredentials(projectName, {
        credentials_json: data.credentials_json,
      })
      const [gsc, ga4] = await Promise.all([
        integrationsApi.test(projectName, 'google_search_console'),
        data.ga4_property_id
          ? integrationsApi.test(projectName, 'google_analytics')
          : Promise.resolve(null),
      ])
      return { gsc, ga4 }
    },
    onSuccess: ({ gsc, ga4 }) => {
      qc.invalidateQueries({ queryKey: ['integrations-status', projectName] })
      if (gsc.connected) {
        toast.success('Google Search Console connected')
        setIsEditing(false)
        reset()
      } else {
        toast.error(`GSC error: ${gsc.error}`)
      }
      if (ga4) {
        if (ga4.connected) toast.success('Google Analytics connected')
        else toast.error(`GA4 error: ${ga4.error}`)
      }
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <div className="space-y-0">
      <SectionWrapper title="Google Search Console" status={gscStatus}>
        <form onSubmit={handleSubmit((d) => mutate(d))} className="space-y-4">
          <Field label="GSC Site URL" error={errors.gsc_site_url?.message}>
            <Input
              {...register('gsc_site_url')}
              placeholder="https://example.com/"
              disabled={locked}
            />
            {!locked && (
              <p className="text-slate-400 text-xs mt-1">
                Must match exactly as verified in Google Search Console
              </p>
            )}
          </Field>
          <Field label="GA4 Property ID (optional)" error={errors.ga4_property_id?.message}>
            <Input
              {...register('ga4_property_id')}
              placeholder={locked ? '••••••••' : '123456789'}
              disabled={locked}
            />
          </Field>
          <Field label="Service Account JSON" error={errors.credentials_json?.message}>
            <Textarea
              {...register('credentials_json')}
              rows={locked ? 3 : 8}
              placeholder={
                locked
                  ? '{ "type": "service_account", ... } — saved'
                  : '{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}'
              }
              disabled={locked}
            />
            {!locked && (
              <p className="text-slate-400 text-xs mt-1">
                Paste the full contents of your Google service account JSON file
              </p>
            )}
          </Field>

          <div className="flex items-center gap-3">
            {locked ? (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
              >
                <Pencil size={13} />
                Edit credentials
              </button>
            ) : (
              <>
                <SaveButton loading={isPending} label="Save & Test All Google" />
                {isConnected && (
                  <button
                    type="button"
                    onClick={() => { setIsEditing(false); reset() }}
                    className="flex items-center gap-2 px-4 py-2 text-slate-500 text-sm font-medium rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                  >
                    <X size={13} />
                    Cancel
                  </button>
                )}
              </>
            )}
            {ga4Status && ga4Status.error !== 'Not enabled in project.yaml' && (
              <StatusBadge
                status={ga4Status.connected ? 'connected' : 'error'}
                label={`GA4: ${ga4Status.connected ? 'OK' : 'Error'}`}
              />
            )}
          </div>
        </form>
      </SectionWrapper>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export function IntegrationsTab({ projectName }: { projectName: string }) {
  const { data: status, isLoading } = useQuery({
    queryKey: ['integrations-status', projectName],
    queryFn: () => integrationsApi.status(projectName),
  })

  const getStatus = (name: string) =>
    status?.integrations.find((i) => i.name === name)

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-400 text-sm py-8">
        <Loader2 size={16} className="animate-spin" />
        Loading integration status...
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <WordPressSection projectName={projectName} status={getStatus('wordpress')} />
      <GoogleSection
        projectName={projectName}
        gscStatus={getStatus('google_search_console')}
        ga4Status={getStatus('google_analytics')}
      />
    </div>
  )
}
