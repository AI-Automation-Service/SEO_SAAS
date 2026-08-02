import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Globe, RefreshCw, FileSearch, Pencil, Check, X, Settings2, Plus } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { projectsApi, integrationsApi, sitemapApi, getErrorMessage } from '@/api/client'
import type { Project } from '@/types/api'
import { cn } from '@/lib/utils'

const INTEGRATION_LABELS: Record<string, string> = {
  wordpress: 'WordPress',
  google_search_console: 'Search Console',
  google_analytics: 'Google Analytics',
}

const TONE_OPTIONS = [
  'Professional',
  'Friendly',
  'Authoritative',
  'Casual',
  'Technical',
  'Conversational',
  'Formal',
]

const SEO_PLUGIN_OPTIONS = [
  { value: 'rankmath', label: 'RankMath' },
  { value: 'yoast', label: 'Yoast SEO' },
  { value: 'aioseo', label: 'AIOSEO' },
  { value: 'none', label: 'No SEO Plugin' },
]

const CONVERSION_OPTIONS = [
  { value: 'lead_generation', label: 'Lead Generation (forms / enquiries)' },
  { value: 'ecommerce', label: 'E-commerce (product sales)' },
  { value: 'phone_call', label: 'Phone Calls' },
  { value: 'email_signup', label: 'Email Signups / Newsletter' },
  { value: 'brand_awareness', label: 'Brand Awareness (content reach)' },
]

// ── Tag Input ────────────────────────────────────────────────────────────────

function TagInput({
  values,
  onChange,
  placeholder,
  disabled,
}: {
  values: string[]
  onChange: (v: string[]) => void
  placeholder: string
  disabled?: boolean
}) {
  const [input, setInput] = useState('')

  function add() {
    const v = input.trim()
    if (v && !values.includes(v)) {
      onChange([...values, v])
      setInput('')
    }
  }

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {values.map((v) => (
          <span
            key={v}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 rounded-md text-xs text-slate-700"
          >
            {v}
            {!disabled && (
              <button
                type="button"
                onClick={() => onChange(values.filter((x) => x !== v))}
                className="text-slate-400 hover:text-red-500 transition-colors cursor-pointer"
              >
                <X size={10} />
              </button>
            )}
          </span>
        ))}
        {values.length === 0 && disabled && (
          <span className="text-xs text-slate-400 italic">None configured</span>
        )}
      </div>
      {!disabled && (
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
            placeholder={placeholder}
            className="flex-1 px-2.5 py-1.5 border border-slate-200 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />
          <button
            type="button"
            onClick={add}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-100 text-slate-600 rounded-md text-xs hover:bg-slate-200 transition-colors cursor-pointer"
          >
            <Plus size={11} />
            Add
          </button>
        </div>
      )}
    </div>
  )
}

// ── Inline website field (existing) ──────────────────────────────────────────

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

  const cancel = () => { setValue(project.website ?? ''); setEditing(false) }

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
          className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer opacity-0 group-hover:opacity-100"
          title="Edit website URL"
        >
          <Pencil size={11} />
        </button>
      </dd>
    </div>
  )
}

// ── Settings form state type ──────────────────────────────────────────────────

interface SettingsForm {
  business_name: string
  business_type: string
  country: string
  language: string
  business_location: string
  tone_of_voice: string
  target_audience: string
  primary_conversion: string
  seo_plugin: string
  seo_goals: string[]
  business_goals: string[]
  competitors: string[]
}

function formFromProject(p: Project): SettingsForm {
  return {
    business_name: p.business_name ?? '',
    business_type: p.business_type ?? '',
    country: p.country ?? '',
    language: p.language ?? '',
    business_location: p.business_location ?? '',
    tone_of_voice: p.tone_of_voice ?? '',
    target_audience: p.target_audience ?? '',
    primary_conversion: p.primary_conversion ?? '',
    seo_plugin: p.seo_plugin ?? '',
    seo_goals: p.seo_goals ?? [],
    business_goals: p.business_goals ?? [],
    competitors: p.competitors ?? [],
  }
}

// ── Project Settings card ─────────────────────────────────────────────────────

function ProjectSettingsCard({ project }: { project: Project }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<SettingsForm>(() => formFromProject(project))

  function field(k: keyof SettingsForm) {
    return {
      value: form[k] as string,
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
        setForm((f) => ({ ...f, [k]: e.target.value })),
    }
  }

  const { mutate, isPending } = useMutation({
    mutationFn: () => projectsApi.update(project.name, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project', project.name] })
      toast.success('Project settings saved')
      setEditing(false)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  function cancel() {
    setForm(formFromProject(project))
    setEditing(false)
  }

  const inputCls = (active: boolean) =>
    cn(
      'w-full px-2.5 py-1.5 rounded-md text-xs border transition-colors',
      active
        ? 'border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white'
        : 'border-transparent bg-transparent text-slate-800 cursor-default',
    )

  const readValue = (v: string) => v || <span className="text-slate-400 italic">Not set</span>

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Settings2 size={15} className="text-slate-400" />
          <h3 className="font-display font-semibold text-slate-900">Project Settings</h3>
        </div>
        {editing ? (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={cancel}
              className="px-3 py-1.5 rounded-lg text-xs text-slate-500 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => mutate()}
              disabled={isPending}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500 text-white hover:bg-emerald-600 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {isPending ? 'Saving...' : 'Save settings'}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => { setForm(formFromProject(project)); setEditing(true) }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-500 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <Pencil size={12} />
            Edit
          </button>
        )}
      </div>

      <div className="space-y-4">
        {/* Row 1: name + type */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Business Name</label>
            {editing
              ? <input {...field('business_name')} className={inputCls(true)} placeholder="My Business" />
              : <p className="text-xs text-slate-800">{readValue(form.business_name)}</p>}
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Business Type</label>
            {editing
              ? <input {...field('business_type')} className={inputCls(true)} placeholder="e.g. SaaS, Agency, E-commerce" />
              : <p className="text-xs text-slate-800">{readValue(form.business_type)}</p>}
          </div>
        </div>

        {/* Row 2: country + language */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Country</label>
            {editing
              ? <input {...field('country')} className={inputCls(true)} placeholder="e.g. Egypt, United States" />
              : <p className="text-xs text-slate-800">{readValue(form.country)}</p>}
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Language</label>
            {editing
              ? <input {...field('language')} className={inputCls(true)} placeholder="e.g. English, Arabic" />
              : <p className="text-xs text-slate-800">{readValue(form.language)}</p>}
          </div>
        </div>

        {/* Business location */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Business Location
            <span className="text-slate-400 font-normal ml-1">(city / region — for local SEO)</span>
          </label>
          {editing
            ? <input {...field('business_location')} className={inputCls(true)} placeholder="e.g. Cairo, Egypt" />
            : <p className="text-xs text-slate-800">{readValue(form.business_location)}</p>}
        </div>

        {/* Row 3: tone + conversion */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Tone of Voice</label>
            {editing ? (
              <select {...field('tone_of_voice')} className={inputCls(true)}>
                <option value="">Select tone…</option>
                {TONE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            ) : (
              <p className="text-xs text-slate-800">{readValue(form.tone_of_voice)}</p>
            )}
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Primary Conversion Goal</label>
            {editing ? (
              <select {...field('primary_conversion')} className={inputCls(true)}>
                <option value="">Select goal…</option>
                {CONVERSION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            ) : (
              <p className="text-xs text-slate-800">
                {CONVERSION_OPTIONS.find(o => o.value === form.primary_conversion)?.label
                  || readValue(form.primary_conversion)}
              </p>
            )}
          </div>
        </div>

        {/* SEO Plugin */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            SEO Plugin
            <span className="text-slate-400 font-normal ml-1">(affects meta tag & schema recommendations)</span>
          </label>
          {editing ? (
            <select {...field('seo_plugin')} className={inputCls(true)}>
              <option value="">Select plugin…</option>
              {SEO_PLUGIN_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          ) : (
            <p className="text-xs text-slate-800">
              {SEO_PLUGIN_OPTIONS.find(o => o.value === form.seo_plugin)?.label
                || readValue(form.seo_plugin)}
            </p>
          )}
        </div>

        {/* Target audience */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Target Audience</label>
          {editing ? (
            <textarea
              {...field('target_audience')}
              rows={2}
              placeholder="e.g. Small business owners in Egypt looking for affordable SEO services"
              className="w-full px-2.5 py-1.5 border border-slate-300 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-emerald-400 resize-none"
            />
          ) : (
            <p className="text-xs text-slate-800 leading-relaxed">{readValue(form.target_audience)}</p>
          )}
        </div>

        {/* Competitors */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Competitors
            <span className="text-slate-400 font-normal ml-1">(used for "Competitor Pages" strategy)</span>
          </label>
          <TagInput
            values={form.competitors}
            onChange={(v) => setForm((f) => ({ ...f, competitors: v }))}
            placeholder="https://competitor.com"
            disabled={!editing}
          />
        </div>

        {/* SEO goals */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">SEO Goals</label>
          <TagInput
            values={form.seo_goals}
            onChange={(v) => setForm((f) => ({ ...f, seo_goals: v }))}
            placeholder="e.g. Rank for local keywords"
            disabled={!editing}
          />
        </div>

        {/* Business goals */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Business Goals</label>
          <TagInput
            values={form.business_goals}
            onChange={(v) => setForm((f) => ({ ...f, business_goals: v }))}
            placeholder="e.g. Generate 50 leads/month"
            disabled={!editing}
          />
        </div>
      </div>
    </div>
  )
}

// ── Main OverviewTab ──────────────────────────────────────────────────────────

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

      {/* Project Settings */}
      <ProjectSettingsCard project={project} />

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

        {isLoading && <p className="text-slate-400 text-sm">Checking integrations...</p>}

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
            {validation.errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
