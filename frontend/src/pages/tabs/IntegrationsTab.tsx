import { forwardRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { Check, ChevronDown, ChevronUp, Eye, EyeOff, Loader2, Pencil, Trash2, X } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { integrationsApi, keysApi, oauthApi, getErrorMessage } from '@/api/client'
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

// ── SEMrush ───────────────────────────────────────────────────────────────────

function SEMrushSection({ isConnected }: { isConnected: boolean }) {
  const qc = useQueryClient()
  const [value, setValue] = useState('')
  const [editing, setEditing] = useState(!isConnected)

  const saveMut = useMutation({
    mutationFn: () => keysApi.save('semrush_key', value),
    onSuccess: () => {
      toast.success('SEMrush API key saved')
      setValue('')
      setEditing(false)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: () => keysApi.delete('semrush_key'),
    onSuccess: () => {
      toast.success('SEMrush key removed')
      setEditing(true)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const status: IntegrationStatusItem = { name: 'semrush', connected: isConnected, error: isConnected ? null : 'Not connected' }

  return (
    <SectionWrapper title="SEMrush (Optional)" status={status}>
      <p className="text-xs text-slate-500 -mt-1">
        Optional — enriches keyword clustering and competitor gap analysis with SEMrush data.
      </p>
      {!editing && isConnected ? (
        <ConnectedRow label="API key stored" onEdit={() => setEditing(true)} onDelete={() => deleteMut.mutate()} deleteLoading={deleteMut.isPending} />
      ) : (
        <div className="space-y-3">
          <Field label="API Key" error={undefined}>
            <PasswordInput value={value} onChange={(e) => setValue(e.target.value)} placeholder="••••••••••••••••" autoComplete="off" />
          </Field>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => saveMut.mutate()}
              disabled={!value.trim() || saveMut.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {saveMut.isPending && <Loader2 size={14} className="animate-spin" />}
              Save Key
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

// ── Ahrefs ────────────────────────────────────────────────────────────────────

function AhrefsSection({ isConnected }: { isConnected: boolean }) {
  const qc = useQueryClient()
  const [value, setValue] = useState('')
  const [editing, setEditing] = useState(!isConnected)

  const saveMut = useMutation({
    mutationFn: () => keysApi.save('ahrefs_key', value),
    onSuccess: () => {
      toast.success('Ahrefs API key saved')
      setValue('')
      setEditing(false)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: () => keysApi.delete('ahrefs_key'),
    onSuccess: () => {
      toast.success('Ahrefs key removed')
      setEditing(true)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const status: IntegrationStatusItem = { name: 'ahrefs', connected: isConnected, error: isConnected ? null : 'Not connected' }

  return (
    <SectionWrapper title="Ahrefs (Optional)" status={status}>
      <p className="text-xs text-slate-500 -mt-1">
        Optional — adds backlink signals and keyword data from Ahrefs to competitor analysis and clustering.
      </p>
      {!editing && isConnected ? (
        <ConnectedRow label="API key stored" onEdit={() => setEditing(true)} onDelete={() => deleteMut.mutate()} deleteLoading={deleteMut.isPending} />
      ) : (
        <div className="space-y-3">
          <Field label="API Key" error={undefined}>
            <PasswordInput value={value} onChange={(e) => setValue(e.target.value)} placeholder="••••••••••••••••" autoComplete="off" />
          </Field>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => saveMut.mutate()}
              disabled={!value.trim() || saveMut.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {saveMut.isPending && <Loader2 size={14} className="animate-spin" />}
              Save Key
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

// ── Moz ───────────────────────────────────────────────────────────────────────

const mozSchema = z.object({
  access_id: z.string().min(1, 'Access ID is required'),
  secret_key: z.string().min(1, 'Secret key is required'),
})
type MozForm = z.infer<typeof mozSchema>

function MozSection({ isConnected }: { isConnected: boolean }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(!isConnected)
  const { register, handleSubmit, reset, formState: { errors } } = useForm<MozForm>({
    resolver: zodResolver(mozSchema),
  })

  const saveMut = useMutation({
    mutationFn: (data: MozForm) =>
      Promise.all([keysApi.save('moz_access_id', data.access_id), keysApi.save('moz_secret_key', data.secret_key)]),
    onSuccess: () => {
      toast.success('Moz credentials saved')
      setEditing(false)
      reset()
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMut = useMutation({
    mutationFn: () => Promise.all([keysApi.delete('moz_access_id'), keysApi.delete('moz_secret_key')]),
    onSuccess: () => {
      toast.success('Moz credentials removed')
      setEditing(true)
      qc.invalidateQueries({ queryKey: ['user-keys'] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const status: IntegrationStatusItem = { name: 'moz', connected: isConnected, error: isConnected ? null : 'Not connected' }

  return (
    <SectionWrapper title="Moz (Optional)" status={status}>
      <p className="text-xs text-slate-500 -mt-1">
        Optional — provides Domain Authority scores used by the SEO Technical audit.
      </p>
      {!editing && isConnected ? (
        <ConnectedRow label="Access ID + Secret key stored" onEdit={() => setEditing(true)} onDelete={() => deleteMut.mutate()} deleteLoading={deleteMut.isPending} />
      ) : (
        <form onSubmit={handleSubmit((d) => saveMut.mutate(d))} className="space-y-3">
          <Field label="Access ID" error={errors.access_id?.message}>
            <Input {...register('access_id')} placeholder="mozscape-..." autoComplete="off" />
          </Field>
          <Field label="Secret Key" error={errors.secret_key?.message}>
            <PasswordInput {...register('secret_key')} placeholder="••••••••••••••••" autoComplete="new-password" />
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

const shopifyManualSchema = z.object({
  store_url: z.string().url('Must be a valid URL, e.g. https://mystore.myshopify.com'),
  access_token: z.string().min(1, 'Access token is required'),
})
type ShopifyManualForm = z.infer<typeof shopifyManualSchema>

function ShopifySection({
  projectName,
  status,
}: {
  projectName: string
  status?: IntegrationStatusItem
}) {
  const isConnected = status?.connected === true
  const [editing, setEditing] = useState(!isConnected)
  const [mode, setMode] = useState<'manual' | 'oauth'>('manual')
  const [shopDomain, setShopDomain] = useState('')
  const qc = useQueryClient()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ShopifyManualForm>({
    resolver: zodResolver(shopifyManualSchema),
  })

  const saveMut = useMutation({
    mutationFn: async (data: ShopifyManualForm) => {
      const envKey = projectName.toUpperCase().replace(/-/g, '_')
      await integrationsApi.updateConfig(projectName, {
        shopify: { enabled: true, store_url: data.store_url, token_env: `SHOPIFY_${envKey}_TOKEN` },
      })
      await integrationsApi.setSecret(projectName, { key: `SHOPIFY_${envKey}_TOKEN`, value: data.access_token })
    },
    onSuccess: () => {
      toast.success('Shopify connected')
      setEditing(false)
      reset()
      qc.invalidateQueries({ queryKey: ['integrations-status', projectName] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const oauthMut = useMutation({
    mutationFn: () => oauthApi.shopifyStart(projectName, shopDomain),
    onSuccess: ({ url }) => {
      window.open(url, '_blank', 'noopener')
      toast.success('Complete the Shopify authorisation in the new tab, then refresh this page.')
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
        <div className="space-y-4">
          {/* Mode tabs */}
          <div className="flex gap-1 p-1 bg-slate-100 rounded-lg w-fit">
            {(['manual', 'oauth'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={cn(
                  'px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
                  mode === m ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'
                )}
              >
                {m === 'manual' ? 'Access Token (Manual)' : 'Partner App OAuth'}
              </button>
            ))}
          </div>

          {mode === 'manual' ? (
            <form onSubmit={handleSubmit((d) => saveMut.mutate(d))} className="space-y-3">
              <Field label="Store URL" error={errors.store_url?.message}>
                <Input {...register('store_url')} placeholder="https://mystore.myshopify.com" />
                <p className="text-slate-400 text-xs mt-1">Use your .myshopify.com URL, not a custom domain</p>
              </Field>
              <Field label="Admin API Access Token" error={errors.access_token?.message}>
                <PasswordInput {...register('access_token')} placeholder="shpat_..." autoComplete="new-password" />
                <p className="text-slate-400 text-xs mt-1">Shopify Admin → Apps → Develop apps → Create an app → Admin API access token</p>
              </Field>
              <div className="flex items-center gap-2">
                <SaveButton loading={saveMut.isPending} label="Connect Shopify" />
                {isConnected && (
                  <button type="button" onClick={() => { setEditing(false); reset() }} className="flex items-center gap-1.5 px-3 py-2 text-slate-500 text-sm rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
                    <X size={13} /> Cancel
                  </button>
                )}
              </div>
            </form>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">Enter your .myshopify.com domain to start the Shopify Partner App OAuth flow.</p>
              <Field label="Shop Domain" error={undefined}>
                <Input
                  value={shopDomain}
                  onChange={(e) => setShopDomain(e.target.value)}
                  placeholder="mystore.myshopify.com"
                />
              </Field>
              <button
                type="button"
                onClick={() => oauthMut.mutate()}
                disabled={!shopDomain.trim() || oauthMut.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-colors cursor-pointer"
              >
                {oauthMut.isPending && <Loader2 size={14} className="animate-spin" />}
                Connect via OAuth
              </button>
            </div>
          )}
        </div>
      )}
    </SectionWrapper>
  )
}

// ── WordPress ─────────────────────────────────────────────────────────────────

const wpAppPasswordSchema = z.object({
  url: z.string().url('Must be a valid URL'),
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'App password is required'),
})
type WpAppPasswordForm = z.infer<typeof wpAppPasswordSchema>

const wpTokenSchema = z.object({
  url: z.string().url('Must be a valid URL'),
  token: z.string().min(10, 'Site token is required'),
})
type WpTokenForm = z.infer<typeof wpTokenSchema>

function WordPressSection({
  projectName,
  status,
}: {
  projectName: string
  status?: IntegrationStatusItem
}) {
  const isConnected = status?.connected === true
  const [isEditing, setIsEditing] = useState(false)
  const [authMode, setAuthMode] = useState<'app_password' | 'plugin_token'>('app_password')
  const locked = isConnected && !isEditing

  const qc = useQueryClient()
  const pwForm = useForm<WpAppPasswordForm>({ resolver: zodResolver(wpAppPasswordSchema) })
  const tokenForm = useForm<WpTokenForm>({ resolver: zodResolver(wpTokenSchema) })

  const pwMut = useMutation({
    mutationFn: async (data: WpAppPasswordForm) => {
      const envKey = projectName.toUpperCase().replace(/-/g, '_')
      await integrationsApi.updateConfig(projectName, {
        wordpress: { enabled: true, url: data.url, username_env: `WP_${envKey}_USERNAME`, password_env: `WP_${envKey}_APP_PASSWORD` },
      })
      await Promise.all([
        integrationsApi.setSecret(projectName, { key: `WP_${envKey}_USERNAME`, value: data.username }),
        integrationsApi.setSecret(projectName, { key: `WP_${envKey}_APP_PASSWORD`, value: data.password }),
      ])
      return integrationsApi.test(projectName, 'wordpress')
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['integrations-status', projectName] })
      if (result.connected) { toast.success('WordPress connected'); setIsEditing(false); pwForm.reset() }
      else toast.error(`WordPress error: ${result.error}`)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const tokenMut = useMutation({
    mutationFn: async (data: WpTokenForm) => {
      const envKey = projectName.toUpperCase().replace(/-/g, '_')
      await integrationsApi.updateConfig(projectName, {
        wordpress: { enabled: true, url: data.url, token_env: `WP_${envKey}_SITE_TOKEN` },
      })
      await integrationsApi.setSecret(projectName, { key: `WP_${envKey}_SITE_TOKEN`, value: data.token })
      return integrationsApi.test(projectName, 'wordpress')
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['integrations-status', projectName] })
      if (result.connected) { toast.success('WordPress connected via site token'); setIsEditing(false); tokenForm.reset() }
      else toast.error(`WordPress error: ${result.error}`)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <SectionWrapper title="WordPress" status={status}>
      {/* Auth mode tabs — only when editing */}
      {(!locked) && (
        <div className="flex gap-1 p-1 bg-slate-100 rounded-lg mb-4 w-fit">
          {(['app_password', 'plugin_token'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setAuthMode(m)}
              className={cn(
                'px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
                authMode === m ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'
              )}
            >
              {m === 'app_password' ? 'App Password' : 'Plugin Token (Phase 3)'}
            </button>
          ))}
        </div>
      )}

      {/* Locked / connected view */}
      {locked ? (
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
          >
            <Pencil size={13} />
            Edit credentials
          </button>
        </div>
      ) : authMode === 'app_password' ? (
        <form onSubmit={pwForm.handleSubmit((d) => pwMut.mutate(d))} className="space-y-4">
          <Field label="Site URL" error={pwForm.formState.errors.url?.message}>
            <Input {...pwForm.register('url')} placeholder="https://example.com" />
          </Field>
          <Field label="Username" error={pwForm.formState.errors.username?.message}>
            <Input {...pwForm.register('username')} placeholder="admin" autoComplete="off" />
          </Field>
          <Field label="Application Password" error={pwForm.formState.errors.password?.message}>
            <Input {...pwForm.register('password')} type="password" placeholder="xxxx xxxx xxxx xxxx" autoComplete="new-password" />
            <p className="text-slate-400 text-xs mt-1">Generate in WordPress → Users → Profile → Application Passwords</p>
          </Field>
          <div className="flex items-center gap-3">
            <SaveButton loading={pwMut.isPending} />
            {isConnected && (
              <button type="button" onClick={() => { setIsEditing(false); pwForm.reset() }} className="flex items-center gap-2 px-4 py-2 text-slate-500 text-sm font-medium rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
                <X size={13} /> Cancel
              </button>
            )}
          </div>
        </form>
      ) : (
        <form onSubmit={tokenForm.handleSubmit((d) => tokenMut.mutate(d))} className="space-y-4">
          <p className="text-xs text-slate-500 -mt-1">
            Install the SEO OS WordPress Plugin on your site. It generates a site token you paste here.
          </p>
          <Field label="Site URL" error={tokenForm.formState.errors.url?.message}>
            <Input {...tokenForm.register('url')} placeholder="https://example.com" />
          </Field>
          <Field label="Site Token" error={tokenForm.formState.errors.token?.message}>
            <PasswordInput {...tokenForm.register('token')} placeholder="seo-os-token-..." autoComplete="new-password" />
            <p className="text-slate-400 text-xs mt-1">Found in WordPress → SEO OS Plugin → Settings → Site Token</p>
          </Field>
          <div className="flex items-center gap-3">
            <SaveButton loading={tokenMut.isPending} label="Save & Test Token" />
            {isConnected && (
              <button type="button" onClick={() => { setIsEditing(false); tokenForm.reset() }} className="flex items-center gap-2 px-4 py-2 text-slate-500 text-sm font-medium rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
                <X size={13} /> Cancel
              </button>
            )}
          </div>
        </form>
      )}
    </SectionWrapper>
  )
}

// ── Google ────────────────────────────────────────────────────────────────────

const googleSiteSchema = z.object({
  gsc_site_url: z.string().url('Must be a valid URL'),
  ga4_property_id: z.string().optional(),
})
type GoogleSiteForm = z.infer<typeof googleSiteSchema>

const googleServiceAccountSchema = z.object({
  gsc_site_url: z.string().url('Must be a valid URL'),
  ga4_property_id: z.string().optional(),
  credentials_json: z.string().min(10, 'Paste the full service account JSON'),
})
type GoogleServiceAccountForm = z.infer<typeof googleServiceAccountSchema>

function GoogleSection({
  projectName,
  gscStatus,
  ga4Status,
  isOAuthConnected,
}: {
  projectName: string
  gscStatus?: IntegrationStatusItem
  ga4Status?: IntegrationStatusItem
  isOAuthConnected: boolean
}) {
  const isConnected = gscStatus?.connected === true || isOAuthConnected
  const [mode, setMode] = useState<'oauth' | 'service_account'>('oauth')
  const [isEditing, setIsEditing] = useState(false)

  const qc = useQueryClient()

  // Site URL / property config form (used after OAuth connect)
  const siteForm = useForm<GoogleSiteForm>({ resolver: zodResolver(googleSiteSchema) })

  // Service account form (legacy)
  const saForm = useForm<GoogleServiceAccountForm>({ resolver: zodResolver(googleServiceAccountSchema) })

  // Google OAuth flow
  const oauthMut = useMutation({
    mutationFn: () => oauthApi.googleStart(),
    onSuccess: ({ url }) => {
      window.open(url, '_blank', 'width=600,height=700,noopener')
      toast.success('Complete the Google sign-in in the new window, then refresh this page.')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  // Save site URL / property config after OAuth
  const siteMut = useMutation({
    mutationFn: (data: GoogleSiteForm) =>
      integrationsApi.updateConfig(projectName, {
        google: {
          enabled: true,
          gsc_site_url: data.gsc_site_url,
          ga4_property_id: data.ga4_property_id || '',
        },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integrations-status', projectName] })
      toast.success('Google site config saved')
      setIsEditing(false)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  // Service account (legacy) save
  const saMut = useMutation({
    mutationFn: async (data: GoogleServiceAccountForm) => {
      try {
        const parsed = JSON.parse(data.credentials_json)
        if (parsed.type !== 'service_account') throw new Error('Expected type: service_account')
      } catch (e) {
        throw new Error(e instanceof Error ? e.message : 'Invalid JSON')
      }
      await integrationsApi.updateConfig(projectName, {
        google: { enabled: true, gsc_site_url: data.gsc_site_url, ga4_property_id: data.ga4_property_id || '' },
      })
      await integrationsApi.uploadGoogleCredentials(projectName, { credentials_json: data.credentials_json })
      const [gsc, ga4] = await Promise.all([
        integrationsApi.test(projectName, 'google_search_console'),
        data.ga4_property_id ? integrationsApi.test(projectName, 'google_analytics') : Promise.resolve(null),
      ])
      return { gsc, ga4 }
    },
    onSuccess: ({ gsc, ga4 }) => {
      qc.invalidateQueries({ queryKey: ['integrations-status', projectName] })
      if (gsc.connected) { toast.success('Google Search Console connected'); setIsEditing(false); saForm.reset() }
      else toast.error(`GSC error: ${gsc.error}`)
      if (ga4) { if (ga4.connected) toast.success('Google Analytics connected'); else toast.error(`GA4 error: ${ga4.error}`) }
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <div className="space-y-0">
      <SectionWrapper title="Google (GSC + GA4)" status={gscStatus}>
        {/* Mode tabs */}
        {!isConnected && (
          <div className="flex gap-1 p-1 bg-slate-100 rounded-lg mb-4 w-fit">
            {(['oauth', 'service_account'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={cn(
                  'px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
                  mode === m ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'
                )}
              >
                {m === 'oauth' ? 'Google OAuth (Recommended)' : 'Service Account (Legacy)'}
              </button>
            ))}
          </div>
        )}

        {/* OAuth connected state */}
        {isOAuthConnected && !isEditing && (
          <div className="space-y-3">
            <ConnectedRow
              label="Connected via Google OAuth"
              onEdit={() => setIsEditing(true)}
            />
            {ga4Status && ga4Status.error !== 'Not enabled in project.yaml' && (
              <StatusBadge status={ga4Status.connected ? 'connected' : 'error'} label={`GA4: ${ga4Status.connected ? 'OK' : 'Error'}`} />
            )}
          </div>
        )}

        {/* OAuth connected — edit site config */}
        {isOAuthConnected && isEditing && (
          <form onSubmit={siteForm.handleSubmit((d) => siteMut.mutate(d))} className="space-y-4">
            <Field label="GSC Site URL" error={siteForm.formState.errors.gsc_site_url?.message}>
              <Input {...siteForm.register('gsc_site_url')} placeholder="https://example.com/" />
              <p className="text-slate-400 text-xs mt-1">Must match exactly as verified in Google Search Console</p>
            </Field>
            <Field label="GA4 Property ID (optional)" error={siteForm.formState.errors.ga4_property_id?.message}>
              <Input {...siteForm.register('ga4_property_id')} placeholder="123456789" />
            </Field>
            <div className="flex gap-2">
              <SaveButton loading={siteMut.isPending} label="Save Config" />
              <button type="button" onClick={() => setIsEditing(false)} className="flex items-center gap-1.5 px-3 py-2 text-slate-500 text-sm rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
                <X size={13} /> Cancel
              </button>
            </div>
          </form>
        )}

        {/* Service account connected state (legacy) */}
        {!isOAuthConnected && isConnected && !isEditing && (
          <ConnectedRow label="Service account credentials saved" onEdit={() => setIsEditing(true)} />
        )}

        {/* OAuth connect button */}
        {!isConnected && mode === 'oauth' && (
          <div className="space-y-3">
            <p className="text-xs text-slate-500">
              Grant SEO OS read-only access to your Google Search Console and Google Analytics 4. One sign-in covers both.
            </p>
            <button
              type="button"
              onClick={() => oauthMut.mutate()}
              disabled={oauthMut.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {oauthMut.isPending && <Loader2 size={14} className="animate-spin" />}
              Connect with Google
            </button>
          </div>
        )}

        {/* Service account form (legacy / not connected) */}
        {!isOAuthConnected && (!isConnected || isEditing) && mode === 'service_account' && (
          <form onSubmit={saForm.handleSubmit((d) => saMut.mutate(d))} className="space-y-4">
            <Field label="GSC Site URL" error={saForm.formState.errors.gsc_site_url?.message}>
              <Input {...saForm.register('gsc_site_url')} placeholder="https://example.com/" />
              <p className="text-slate-400 text-xs mt-1">Must match exactly as verified in Google Search Console</p>
            </Field>
            <Field label="GA4 Property ID (optional)" error={saForm.formState.errors.ga4_property_id?.message}>
              <Input {...saForm.register('ga4_property_id')} placeholder="123456789" />
            </Field>
            <Field label="Service Account JSON" error={saForm.formState.errors.credentials_json?.message}>
              <Textarea {...saForm.register('credentials_json')} rows={8} placeholder={'{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}'} />
              <p className="text-slate-400 text-xs mt-1">Paste the full contents of your Google service account JSON file</p>
            </Field>
            <div className="flex items-center gap-3">
              <SaveButton loading={saMut.isPending} label="Save & Test" />
              {isConnected && (
                <button type="button" onClick={() => { setIsEditing(false); saForm.reset() }} className="flex items-center gap-2 px-4 py-2 text-slate-500 text-sm font-medium rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
                  <X size={13} /> Cancel
                </button>
              )}
              {ga4Status && ga4Status.error !== 'Not enabled in project.yaml' && (
                <StatusBadge status={ga4Status.connected ? 'connected' : 'error'} label={`GA4: ${ga4Status.connected ? 'OK' : 'Error'}`} />
              )}
            </div>
          </form>
        )}
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
          <CopyscapeSection isConnected={keyConnected('copyscape_user') && keyConnected('copyscape_key')} />
          <DataForSEOSection isConnected={keyConnected('dataforseo_login') && keyConnected('dataforseo_password')} />
          <SEMrushSection isConnected={keyConnected('semrush_key')} />
          <AhrefsSection isConnected={keyConnected('ahrefs_key')} />
          <MozSection isConnected={keyConnected('moz_access_id') && keyConnected('moz_secret_key')} />
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
            isOAuthConnected={keyConnected('google_refresh_token')}
          />
        </div>
      </div>
    </div>
  )
}
