import { forwardRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { Check, ChevronDown, ChevronUp, Eye, EyeOff, Loader2, Pencil, Trash2, X } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { integrationsApi, keysApi, getErrorMessage } from '@/api/client'
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

// ── Shared secret-input + connected-row helpers ───────────────────────────────

const PasswordInput = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  (props, ref) => {
    const [show, setShow] = useState(false)
    return (
      <div className="relative">
        <Input ref={ref} {...props} type={show ? 'text' : 'password'} />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
        >
          {show ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      </div>
    )
  }
)
PasswordInput.displayName = 'PasswordInput'

function ConnectedRow({ label, editLabel = 'Update', onEdit, onDelete, deleteLoading }: {
  label: string
  editLabel?: string
  onEdit: () => void
  onDelete?: () => void
  deleteLoading?: boolean
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg">
        <Check size={13} className="text-emerald-500 shrink-0" />
        <span className="text-sm text-slate-600">{label}</span>
      </div>
      <button
        type="button"
        onClick={onEdit}
        className="flex items-center gap-1.5 px-3 py-2 border border-slate-300 text-slate-600 text-sm rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
      >
        <Pencil size={13} /> {editLabel}
      </button>
      {onDelete && (
        <button
          type="button"
          onClick={onDelete}
          disabled={deleteLoading}
          className="flex items-center gap-1.5 px-3 py-2 border border-red-200 text-red-500 text-sm rounded-lg hover:bg-red-50 transition-colors cursor-pointer disabled:opacity-50"
        >
          <Trash2 size={13} />
        </button>
      )}
    </div>
  )
}

// ── OpenAI API Key ────────────────────────────────────────────────────────────

function OpenAISection({ isConnected }: { isConnected: boolean }) {
  const qc = useQueryClient()
  const [value, setValue] = useState('')
  const [editing, setEditing] = useState(!isConnected)

  const saveMut = useMutation({
    mutationFn: async () => {
      await keysApi.test('openai', value)
      await keysApi.save('openai', value)
    },
    onSuccess: () => {
      toast.success('OpenAI key saved and verified')
      setValue('')
      setEditing(false)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: () => keysApi.delete('openai'),
    onSuccess: () => {
      toast.success('OpenAI key removed')
      setEditing(true)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <SectionWrapper title="OpenAI API Key" status={isConnected ? { name: 'openai', connected: true } : { name: 'openai', connected: false, error: 'Not connected' }}>
      {!editing && isConnected ? (
        <ConnectedRow label="Key stored securely" onEdit={() => setEditing(true)} onDelete={() => deleteMut.mutate()} deleteLoading={deleteMut.isPending} />
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            Required for all AI features. Get yours at{' '}
            <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-emerald-600 underline hover:text-emerald-700">
              platform.openai.com/api-keys
            </a>
          </p>
          <Field label="API Key" error={undefined}>
            <PasswordInput value={value} onChange={(e) => setValue(e.target.value)} placeholder="sk-proj-..." autoComplete="off" />
          </Field>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => saveMut.mutate()}
              disabled={!value.trim() || saveMut.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {saveMut.isPending && <Loader2 size={14} className="animate-spin" />}
              {saveMut.isPending ? 'Testing & Saving…' : 'Test & Save'}
            </button>
            {isConnected && (
              <button
                type="button"
                onClick={() => { setEditing(false); setValue('') }}
                className="flex items-center gap-1.5 px-3 py-2 text-slate-500 text-sm rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X size={13} /> Cancel
              </button>
            )}
          </div>
        </div>
      )}
    </SectionWrapper>
  )
}

// ── Copyscape ─────────────────────────────────────────────────────────────────

const copyscapeSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  api_key: z.string().min(1, 'API key is required'),
})
type CopyscapeForm = z.infer<typeof copyscapeSchema>

function CopyscapeSection({ isConnected }: { isConnected: boolean }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(!isConnected)

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CopyscapeForm>({
    resolver: zodResolver(copyscapeSchema),
  })

  const saveMut = useMutation({
    mutationFn: (data: CopyscapeForm) =>
      Promise.all([keysApi.save('copyscape_user', data.username), keysApi.save('copyscape_key', data.api_key)]),
    onSuccess: () => {
      toast.success('Copyscape credentials saved')
      setEditing(false)
      reset()
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: () => Promise.all([keysApi.delete('copyscape_user'), keysApi.delete('copyscape_key')]),
    onSuccess: () => {
      toast.success('Copyscape credentials removed')
      setEditing(true)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const status: IntegrationStatusItem = { name: 'copyscape', connected: isConnected, error: isConnected ? null : 'Not connected' }

  return (
    <SectionWrapper title="Copyscape (Plagiarism Check)" status={status}>
      <p className="text-xs text-slate-500 -mt-1">
        Optional — used to check generated articles for plagiarism before publishing. Without this, plagiarism checks are skipped.
      </p>
      {!editing && isConnected ? (
        <ConnectedRow label="Username + API key stored" onEdit={() => setEditing(true)} onDelete={() => deleteMut.mutate()} deleteLoading={deleteMut.isPending} />
      ) : (
        <form onSubmit={handleSubmit((d) => saveMut.mutate(d))} className="space-y-3">
          <Field label="Copyscape Username" error={errors.username?.message}>
            <Input {...register('username')} placeholder="your_copyscape_username" autoComplete="off" />
          </Field>
          <Field label="API Key" error={errors.api_key?.message}>
            <PasswordInput {...register('api_key')} placeholder="••••••••••••••••" autoComplete="new-password" />
            <p className="text-slate-400 text-xs mt-1">Find your API key at copyscape.com → Account Settings</p>
          </Field>
          <div className="flex items-center gap-2">
            <SaveButton loading={saveMut.isPending} label="Save Credentials" />
            {isConnected && (
              <button type="button" onClick={() => { setEditing(false); reset() }} className="flex items-center gap-1.5 px-3 py-2 text-slate-500 text-sm rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
                <X size={13} /> Cancel
              </button>
            )}
          </div>
        </form>
      )}
    </SectionWrapper>
  )
}

// ── Google API Key ────────────────────────────────────────────────────────────

function GoogleAPIKeySection({ isConnected }: { isConnected: boolean }) {
  const qc = useQueryClient()
  const [value, setValue] = useState('')
  const [editing, setEditing] = useState(!isConnected)

  const saveMut = useMutation({
    mutationFn: async () => {
      await keysApi.test('google_api_key', value)
      await keysApi.save('google_api_key', value)
    },
    onSuccess: () => {
      toast.success('Google API key saved and verified')
      setValue('')
      setEditing(false)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: () => keysApi.delete('google_api_key'),
    onSuccess: () => {
      toast.success('Google API key removed')
      setEditing(true)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const status: IntegrationStatusItem = { name: 'google_api_key', connected: isConnected, error: isConnected ? null : 'Not connected' }

  return (
    <SectionWrapper title="Google API Key (PageSpeed)" status={status}>
      <p className="text-xs text-slate-500 -mt-1">
        Required for Core Web Vitals and PageSpeed audits. Free — create one in{' '}
        <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-emerald-600 underline hover:text-emerald-700">
          Google Cloud Console
        </a>
        {' '}with PageSpeed Insights API enabled.
      </p>
      {!editing && isConnected ? (
        <ConnectedRow label="Key stored securely" onEdit={() => setEditing(true)} onDelete={() => deleteMut.mutate()} deleteLoading={deleteMut.isPending} />
      ) : (
        <div className="space-y-3">
          <Field label="API Key" error={undefined}>
            <PasswordInput value={value} onChange={(e) => setValue(e.target.value)} placeholder="AIza..." autoComplete="off" />
          </Field>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => saveMut.mutate()}
              disabled={!value.trim() || saveMut.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {saveMut.isPending && <Loader2 size={14} className="animate-spin" />}
              {saveMut.isPending ? 'Testing & Saving…' : 'Test & Save'}
            </button>
            {isConnected && (
              <button type="button" onClick={() => { setEditing(false); setValue('') }} className="flex items-center gap-1.5 px-3 py-2 text-slate-500 text-sm rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
                <X size={13} /> Cancel
              </button>
            )}
          </div>
        </div>
      )}
    </SectionWrapper>
  )
}

// ── DataForSEO ────────────────────────────────────────────────────────────────

const dataForSEOSchema = z.object({
  login: z.string().min(1, 'Login is required'),
  password: z.string().min(1, 'Password is required'),
})
type DataForSEOForm = z.infer<typeof dataForSEOSchema>

function DataForSEOSection({ isConnected }: { isConnected: boolean }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(!isConnected)

  const { register, handleSubmit, reset, formState: { errors } } = useForm<DataForSEOForm>({
    resolver: zodResolver(dataForSEOSchema),
  })

  const saveMut = useMutation({
    mutationFn: (data: DataForSEOForm) =>
      Promise.all([keysApi.save('dataforseo_login', data.login), keysApi.save('dataforseo_password', data.password)]),
    onSuccess: () => {
      toast.success('DataForSEO credentials saved')
      setEditing(false)
      reset()
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: () => Promise.all([keysApi.delete('dataforseo_login'), keysApi.delete('dataforseo_password')]),
    onSuccess: () => {
      toast.success('DataForSEO credentials removed')
      setEditing(true)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const status: IntegrationStatusItem = { name: 'dataforseo', connected: isConnected, error: isConnected ? null : 'Not connected' }

  return (
    <SectionWrapper title="DataForSEO (Optional)" status={status}>
      <p className="text-xs text-slate-500 -mt-1">
        Optional — adds real keyword difficulty scores to analysis. Without this, keyword volume/difficulty data uses GSC estimates.
      </p>
      {!editing && isConnected ? (
        <ConnectedRow label="Login + password stored" onEdit={() => setEditing(true)} onDelete={() => deleteMut.mutate()} deleteLoading={deleteMut.isPending} />
      ) : (
        <form onSubmit={handleSubmit((d) => saveMut.mutate(d))} className="space-y-3">
          <Field label="DataForSEO Login (email)" error={errors.login?.message}>
            <Input {...register('login')} placeholder="your@email.com" autoComplete="off" />
          </Field>
          <Field label="Password" error={errors.password?.message}>
            <PasswordInput {...register('password')} placeholder="••••••••••••••••" autoComplete="new-password" />
          </Field>
          <div className="flex items-center gap-2">
            <SaveButton loading={saveMut.isPending} label="Save Credentials" />
            {isConnected && (
              <button type="button" onClick={() => { setEditing(false); reset() }} className="flex items-center gap-1.5 px-3 py-2 text-slate-500 text-sm rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
                <X size={13} /> Cancel
              </button>
            )}
          </div>
        </form>
      )}
    </SectionWrapper>
  )
}

// ── Shopify ───────────────────────────────────────────────────────────────────

const shopifySchema = z.object({
  store_url: z.string().url('Must be a valid URL, e.g. https://mystore.myshopify.com'),
  access_token: z.string().min(1, 'Access token is required'),
})
type ShopifyForm = z.infer<typeof shopifySchema>

function ShopifySection({
  projectName,
  status,
}: {
  projectName: string
  status?: IntegrationStatusItem
}) {
  const isConnected = status?.connected === true
  const [editing, setEditing] = useState(!isConnected)
  const qc = useQueryClient()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ShopifyForm>({
    resolver: zodResolver(shopifySchema),
  })

  const saveMut = useMutation({
    mutationFn: async (data: ShopifyForm) => {
      const envKey = projectName.toUpperCase().replace(/-/g, '_')
      await integrationsApi.updateConfig(projectName, {
        shopify: {
          enabled: true,
          store_url: data.store_url,
          token_env: `SHOPIFY_${envKey}_TOKEN`,
        },
      })
      await integrationsApi.setSecret(projectName, {
        key: `SHOPIFY_${envKey}_TOKEN`,
        value: data.access_token,
      })
    },
    onSuccess: () => {
      toast.success('Shopify connected')
      setEditing(false)
      reset()
      qc.invalidateQueries({ queryKey: ['integrations-status', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <SectionWrapper title="Shopify" status={status}>
      <p className="text-xs text-slate-500 -mt-1">
        Connect your Shopify store to enable AI-powered SEO improvements for products, collections, pages, and articles.
      </p>
      {!editing && isConnected ? (
        <ConnectedRow label="Store connected" editLabel="Edit" onEdit={() => setEditing(true)} />
      ) : (
        <form onSubmit={handleSubmit((d) => saveMut.mutate(d))} className="space-y-3">
          <Field label="Store URL" error={errors.store_url?.message}>
            <Input {...register('store_url')} placeholder="https://mystore.myshopify.com" />
            <p className="text-slate-400 text-xs mt-1">Use your .myshopify.com URL, not a custom domain</p>
          </Field>
          <Field label="Admin API Access Token" error={errors.access_token?.message}>
            <PasswordInput {...register('access_token')} placeholder="shpat_..." autoComplete="new-password" />
            <p className="text-slate-400 text-xs mt-1">
              Create in Shopify Admin → Apps → Develop apps → Create an app → Admin API access token
            </p>
          </Field>
          <div className="flex items-center gap-2">
            <SaveButton loading={saveMut.isPending} label="Connect Shopify" />
            {isConnected && (
              <button
                type="button"
                onClick={() => { setEditing(false); reset() }}
                className="flex items-center gap-1.5 px-3 py-2 text-slate-500 text-sm rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X size={13} /> Cancel
              </button>
            )}
          </div>
        </form>
      )}
    </SectionWrapper>
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
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['integrations-status', projectName],
    queryFn: () => integrationsApi.status(projectName),
  })

  const { data: userKeys = [], isLoading: keysLoading } = useQuery({
    queryKey: ['user-keys'],
    queryFn: () => keysApi.list(),
    staleTime: 5 * 60_000,
  })

  const getStatus = (name: string) =>
    status?.integrations.find((i) => i.name === name)

  const keyConnected = (service: string) =>
    userKeys.find((k) => k.service === service)?.connected ?? false

  if (statusLoading || keysLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-400 text-sm py-8">
        <Loader2 size={16} className="animate-spin" />
        Loading integration status...
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Account-level Keys</h3>
        <div className="space-y-4">
          <OpenAISection isConnected={keyConnected('openai')} />
          <GoogleAPIKeySection isConnected={keyConnected('google_api_key')} />
          <CopyscapeSection isConnected={keyConnected('copyscape_user') && keyConnected('copyscape_key')} />
          <DataForSEOSection isConnected={keyConnected('dataforseo_login') && keyConnected('dataforseo_password')} />
        </div>
      </div>
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Project Integrations</h3>
        <div className="space-y-4">
          <WordPressSection projectName={projectName} status={getStatus('wordpress')} />
          <ShopifySection projectName={projectName} status={getStatus('shopify')} />
          <GoogleSection
            projectName={projectName}
            gscStatus={getStatus('google_search_console')}
            ga4Status={getStatus('google_analytics')}
          />
        </div>
      </div>
    </div>
  )
}
