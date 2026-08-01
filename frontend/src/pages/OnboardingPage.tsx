import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, ChevronDown, ChevronUp, ExternalLink, Eye, EyeOff, Loader2, Upload } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi, keysApi, projectsApi, integrationsApi, getErrorMessage } from '@/api/client'
import { useAuth } from '@/context/AuthContext'

// ── Step config ───────────────────────────────────────────────────────────────

const STEPS = [
  { id: 1, title: 'OpenAI API Key', subtitle: 'Connect your AI provider' },
  { id: 2, title: 'Create Project', subtitle: 'Set up your first website' },
  { id: 3, title: 'WordPress', subtitle: 'Connect your CMS' },
  { id: 4, title: 'Search Console', subtitle: 'Connect GSC data' },
  { id: 5, title: 'Google Analytics', subtitle: 'Connect GA4 data' },
  { id: 6, title: 'PageSpeed API Key', subtitle: 'Enable performance analysis' },
]

// ── Guide accordion ───────────────────────────────────────────────────────────

function Guide({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl overflow-hidden mb-6">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-blue-100/50 transition-colors cursor-pointer"
      >
        <span className="text-blue-800 text-sm font-semibold">{title}</span>
        {open ? <ChevronUp size={15} className="text-blue-600 shrink-0" /> : <ChevronDown size={15} className="text-blue-600 shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4 text-sm text-blue-900 space-y-2 border-t border-blue-200 pt-3">
          {children}
        </div>
      )}
    </div>
  )
}

function GuideStep({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <div className="flex gap-2.5">
      <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">{n}</span>
      <span className="leading-relaxed">{children}</span>
    </div>
  )
}

function ExternalA({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-blue-700 underline hover:text-blue-900 font-medium">
      {children}
      <ExternalLink size={11} />
    </a>
  )
}

// ── Shared form elements ──────────────────────────────────────────────────────

const inputCls = 'w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent transition'

function Label({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wide">{children}</label>
}

function PrimaryBtn({ loading, children, disabled, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean }) {
  return (
    <button
      type="submit"
      disabled={loading || disabled}
      className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
      {...props}
    >
      {loading && <Loader2 size={14} className="animate-spin" />}
      {children}
    </button>
  )
}

// ── Step 1: OpenAI Key ────────────────────────────────────────────────────────

function Step1({ onComplete }: { onComplete: () => void }) {
  const [key, setKey] = useState('')
  const [show, setShow] = useState(false)
  const [saving, setSaving] = useState(false)

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!key.trim()) return
    setSaving(true)
    try {
      await keysApi.test('openai', key.trim())
      await keysApi.save('openai', key.trim())
      toast.success('OpenAI key connected')
      onComplete()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <Guide title="How to get an OpenAI API key?">
        <GuideStep n={1}>
          Visit <ExternalA href="https://platform.openai.com/signup">platform.openai.com</ExternalA> and create an account or sign in.
        </GuideStep>
        <GuideStep n={2}>
          In the top-right, click on your profile icon and select <strong>API keys</strong> — or go directly to <ExternalA href="https://platform.openai.com/api-keys">platform.openai.com/api-keys</ExternalA>.
        </GuideStep>
        <GuideStep n={3}>
          Click <strong>"Create new secret key"</strong>, give it a name (e.g. "SEO OS"), and click Create.
        </GuideStep>
        <GuideStep n={4}>
          Copy the key immediately — it will only be shown once. Paste it in the field below.
        </GuideStep>
        <GuideStep n={5}>
          Make sure your OpenAI account has billing enabled at <ExternalA href="https://platform.openai.com/settings/organization/billing">platform.openai.com/billing</ExternalA>, or the key won't work for content generation.
        </GuideStep>
      </Guide>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <Label>OpenAI API Key</Label>
          <div className="relative">
            <input
              type={show ? 'text' : 'password'}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="sk-proj-..."
              className={inputCls + ' pr-10'}
              autoComplete="off"
              required
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
              tabIndex={-1}
            >
              {show ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-1.5">Stored encrypted — never shared or logged</p>
        </div>
        <PrimaryBtn loading={saving}>
          Test & Save — Continue →
        </PrimaryBtn>
      </form>
    </div>
  )
}

// ── Step 2: Create Project ────────────────────────────────────────────────────

function Step2({ onComplete }: { onComplete: (projectName: string) => void }) {
  const [name, setName] = useState('')
  const [cms, setCms] = useState('wordpress')
  const [website, setWebsite] = useState('')
  const [creating, setCreating] = useState(false)

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setCreating(true)
    try {
      await projectsApi.create({ name: name.trim().toLowerCase().replace(/\s+/g, '-'), cms })
      if (website.trim()) {
        await projectsApi.update(name.trim().toLowerCase().replace(/\s+/g, '-'), { website: website.trim() })
      }
      toast.success('Project created')
      onComplete(name.trim().toLowerCase().replace(/\s+/g, '-'))
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setCreating(false)
    }
  }

  return (
    <form onSubmit={handleCreate} className="space-y-4">
      <div>
        <Label>Project Name</Label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="my-website"
          className={inputCls}
          required
        />
        <p className="text-xs text-slate-400 mt-1.5">Lowercase letters, numbers, hyphens only. E.g. "my-blog"</p>
      </div>
      <div>
        <Label>CMS / Platform</Label>
        <select value={cms} onChange={(e) => setCms(e.target.value)} className={inputCls}>
          <option value="wordpress">WordPress</option>
          <option value="shopify">Shopify</option>
          <option value="static">Static / Other</option>
        </select>
      </div>
      <div>
        <Label>Website URL</Label>
        <input
          type="url"
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
          placeholder="https://example.com"
          className={inputCls}
        />
        <p className="text-xs text-slate-400 mt-1.5">Optional — you can update this later</p>
      </div>
      <PrimaryBtn loading={creating}>
        Create Project — Continue →
      </PrimaryBtn>
    </form>
  )
}

// ── Step 3: WordPress ─────────────────────────────────────────────────────────

function Step3({ projectName, onComplete }: { projectName: string; onComplete: () => void }) {
  const [url, setUrl] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const envKey = projectName.toUpperCase().replace(/-/g, '_')
      await integrationsApi.updateConfig(projectName, {
        wordpress: {
          enabled: true,
          url,
          username_env: `WP_${envKey}_USERNAME`,
          password_env: `WP_${envKey}_APP_PASSWORD`,
        },
      })
      await integrationsApi.setSecret(projectName, { key: `WP_${envKey}_USERNAME`, value: username })
      await integrationsApi.setSecret(projectName, { key: `WP_${envKey}_APP_PASSWORD`, value: password })
      const result = await integrationsApi.test(projectName, 'wordpress')
      if (result.connected) {
        toast.success('WordPress connected!')
        onComplete()
      } else {
        toast.error(`Connection failed: ${result.error}`)
      }
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <Guide title="How to get a WordPress Application Password?">
        <GuideStep n={1}>
          Log in to your WordPress admin dashboard at <strong>yourdomain.com/wp-admin</strong>.
        </GuideStep>
        <GuideStep n={2}>
          In the left menu go to <strong>Users → Profile</strong>.
        </GuideStep>
        <GuideStep n={3}>
          Scroll all the way down to the <strong>"Application Passwords"</strong> section.
        </GuideStep>
        <GuideStep n={4}>
          In the "New Application Password Name" field, type <strong>SEO OS</strong> and click <strong>"Add New Application Password"</strong>.
        </GuideStep>
        <GuideStep n={5}>
          Copy the password shown (format: xxxx xxxx xxxx xxxx). It will only appear once.
        </GuideStep>
        <GuideStep n={6}>
          Paste your WordPress username and the application password below.
        </GuideStep>
        <p className="text-xs text-blue-700 mt-1 font-medium">
          Note: Application Passwords require WordPress 5.6+ and HTTPS on your site.
        </p>
      </Guide>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <Label>WordPress Site URL</Label>
          <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://yourdomain.com" className={inputCls} required />
        </div>
        <div>
          <Label>WordPress Username</Label>
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="admin" className={inputCls} autoComplete="off" required />
        </div>
        <div>
          <Label>Application Password</Label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="xxxx xxxx xxxx xxxx" className={inputCls} autoComplete="new-password" required />
        </div>
        <PrimaryBtn loading={saving}>
          Save & Test Connection →
        </PrimaryBtn>
      </form>
    </div>
  )
}

// ── Step 4: Google Search Console ─────────────────────────────────────────────

function Step4({ projectName, onComplete }: { projectName: string; onComplete: () => void }) {
  const [credJson, setCredJson] = useState('')
  const [gscUrl, setGscUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => setCredJson((ev.target?.result as string) ?? '')
    reader.readAsText(file)
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!credJson.trim()) { toast.error('Paste or upload your service account JSON'); return }
    setSaving(true)
    try {
      let parsed: Record<string, unknown>
      try {
        parsed = JSON.parse(credJson)
      } catch {
        throw new Error('Invalid JSON — paste the full service account file content')
      }
      if (parsed.type !== 'service_account') {
        throw new Error('Expected a service account JSON (must have "type": "service_account")')
      }

      await integrationsApi.updateConfig(projectName, {
        google: { enabled: true, gsc_site_url: gscUrl, ga4_property_id: '' },
      })
      await integrationsApi.uploadGoogleCredentials(projectName, { credentials_json: credJson })
      const result = await integrationsApi.test(projectName, 'google_search_console')
      if (result.connected) {
        toast.success('Google Search Console connected!')
        onComplete()
      } else {
        toast.error(`GSC failed: ${result.error}`)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <Guide title="How to set up Google Search Console access?">
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-emerald-800 text-xs mb-3">
          <strong>100% FREE</strong> — Google Cloud will ask for a payment method when you first sign up, but the APIs we use (Search Console, Analytics &amp; PageSpeed) are completely free. You will not be charged. New accounts also receive $300 in free credits.
        </div>
        <p className="font-semibold text-blue-800 text-xs uppercase tracking-wide mb-2">Part 1 — Create a Google Cloud account &amp; project</p>
        <GuideStep n={1}>
          Go to <ExternalA href="https://console.cloud.google.com">console.cloud.google.com</ExternalA>. If this is your first time, click <strong>"Get started for free"</strong>, sign in with your Google account, and follow the steps to activate your account — you'll need to add a payment method, but you won't be charged for these APIs.
        </GuideStep>
        <GuideStep n={2}>
          Once inside, click the project dropdown at the top → <strong>"New Project"</strong>. Give it a name (e.g. "SEO OS") and click <strong>Create</strong>.
        </GuideStep>
        <GuideStep n={3}>
          In the left menu go to <strong>APIs &amp; Services → Library</strong>. Search for <strong>"Google Search Console API"</strong> and click <strong>Enable</strong>.
        </GuideStep>
        <GuideStep n={4}>
          Go to <strong>IAM &amp; Admin → Service Accounts</strong>.
        </GuideStep>
        <GuideStep n={5}>
          Click <strong>"Create Service Account"</strong>. Give it a name (e.g. "seo-os") and click <strong>Done</strong> (no roles needed).
        </GuideStep>
        <GuideStep n={6}>
          Click on the service account → <strong>Keys</strong> tab → <strong>Add Key → Create new key → JSON</strong>. A JSON file will download automatically.
        </GuideStep>

        <p className="font-semibold text-blue-800 text-xs uppercase tracking-wide mb-2 mt-4">Part 2 — Add service account to GSC property</p>
        <GuideStep n={7}>
          Open the downloaded JSON and copy the value of <strong>"client_email"</strong> (looks like seo-os@project-id.iam.gserviceaccount.com).
        </GuideStep>
        <GuideStep n={8}>
          Go to <ExternalA href="https://search.google.com/search-console">Google Search Console</ExternalA> and select your property.
        </GuideStep>
        <GuideStep n={9}>
          Go to <strong>Settings → Users and permissions → Add user</strong>. Paste the service account email and set permission to <strong>Full</strong>.
        </GuideStep>
        <GuideStep n={10}>
          Your GSC site URL must exactly match what's in GSC (e.g. <code className="bg-blue-100 px-1 rounded">https://example.com/</code> or <code className="bg-blue-100 px-1 rounded">sc-domain:example.com</code>).
        </GuideStep>
      </Guide>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <Label>Service Account Credentials (JSON)</Label>
          <div className="flex gap-2 mb-2">
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 text-slate-600 text-xs font-medium rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
            >
              <Upload size={13} />
              Upload JSON file
            </button>
            {credJson && (
              <span className="flex items-center gap-1 text-emerald-600 text-xs font-medium">
                <CheckCircle2 size={13} /> File loaded
              </span>
            )}
          </div>
          <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={handleFileUpload} />
          <textarea
            value={credJson}
            onChange={(e) => setCredJson(e.target.value)}
            placeholder={'{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}'}
            rows={6}
            className="w-full px-3 py-2.5 text-xs font-mono border border-gray-200 rounded-lg bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none transition"
            required
          />
        </div>
        <div>
          <Label>GSC Property URL</Label>
          <input
            type="text"
            value={gscUrl}
            onChange={(e) => setGscUrl(e.target.value)}
            placeholder="https://example.com/ or sc-domain:example.com"
            className={inputCls}
            required
          />
        </div>
        <PrimaryBtn loading={saving}>
          Save & Test GSC Connection →
        </PrimaryBtn>
      </form>
    </div>
  )
}

// ── Step 5: Google Analytics 4 ────────────────────────────────────────────────

function Step5({ projectName, onComplete }: { projectName: string; onComplete: () => void }) {
  const [propertyId, setPropertyId] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await integrationsApi.updateConfig(projectName, {
        google: { ga4_property_id: propertyId.trim() },
      })
      const result = await integrationsApi.test(projectName, 'google_analytics')
      if (result.connected) {
        toast.success('Google Analytics 4 connected!')
        onComplete()
      } else {
        toast.error(`GA4 failed: ${result.error}`)
      }
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <Guide title="How to connect Google Analytics 4?">
        <p className="text-xs text-blue-700 mb-2">This step reuses the service account you created in the previous step.</p>
        <GuideStep n={1}>
          Go to <ExternalA href="https://analytics.google.com">Google Analytics</ExternalA> and select your account and GA4 property.
        </GuideStep>
        <GuideStep n={2}>
          Click the <strong>gear icon (Admin)</strong> at the bottom-left.
        </GuideStep>
        <GuideStep n={3}>
          Under the <strong>Property</strong> column, click <strong>"Property Access Management"</strong>.
        </GuideStep>
        <GuideStep n={4}>
          Click the <strong>"+"</strong> icon → <strong>"Add users"</strong>. Paste the service account email from Step 4 (client_email in the JSON).
        </GuideStep>
        <GuideStep n={5}>
          Set the role to <strong>Viewer</strong> and click <strong>Add</strong>.
        </GuideStep>
        <GuideStep n={6}>
          To find your Property ID: still in Admin, click <strong>"Property Settings"</strong> — the Property ID is shown at the top (e.g. <code className="bg-blue-100 px-1 rounded">1234567890</code>).
        </GuideStep>
      </Guide>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <Label>GA4 Property ID</Label>
          <input
            type="text"
            value={propertyId}
            onChange={(e) => setPropertyId(e.target.value)}
            placeholder="1234567890"
            className={inputCls}
            required
          />
          <p className="text-xs text-slate-400 mt-1.5">Numbers only, found in GA4 Admin → Property Settings</p>
        </div>
        <PrimaryBtn loading={saving}>
          Save & Test GA4 Connection →
        </PrimaryBtn>
      </form>
    </div>
  )
}

// ── Step 6: PageSpeed API Key ─────────────────────────────────────────────────

function Step6({ onComplete }: { onComplete: () => void }) {
  const [key, setKey] = useState('')
  const [show, setShow] = useState(false)
  const [saving, setSaving] = useState(false)

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await keysApi.save('google_api_key', key.trim())
      toast.success('Google API key saved!')
      onComplete()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <Guide title="How to get a Google API Key for PageSpeed?">
        <GuideStep n={1}>
          Go to <ExternalA href="https://console.cloud.google.com">Google Cloud Console</ExternalA> and select the same project from Step 4.
        </GuideStep>
        <GuideStep n={2}>
          Go to <strong>APIs &amp; Services → Library</strong>. Search for <strong>"PageSpeed Insights API"</strong> and click <strong>Enable</strong>.
        </GuideStep>
        <GuideStep n={3}>
          Go to <strong>APIs &amp; Services → Credentials</strong>.
        </GuideStep>
        <GuideStep n={4}>
          Click <strong>"Create Credentials" → "API key"</strong>. Copy the key shown.
        </GuideStep>
        <GuideStep n={5}>
          Click on the newly created key to open its settings. Under <strong>"Application restrictions"</strong>, select <strong>None</strong> and click Save.
        </GuideStep>
        <GuideStep n={6}>
          Paste the key below and click Complete Setup.
        </GuideStep>
        <p className="text-xs text-blue-700 mt-1 font-medium">
          Warning: Leaving Application restrictions set to "HTTP referrers" will cause 403 errors since requests come from our server.
        </p>
      </Guide>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <Label>Google API Key</Label>
          <div className="relative">
            <input
              type={show ? 'text' : 'password'}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="AIza..."
              className={inputCls + ' pr-10'}
              autoComplete="off"
              required
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
              tabIndex={-1}
            >
              {show ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>
        <PrimaryBtn loading={saving}>
          Test & Complete Setup →
        </PrimaryBtn>
      </form>
    </div>
  )
}

// ── Main wizard page ──────────────────────────────────────────────────────────

export function OnboardingPage() {
  const { refreshUser } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set())
  const [projectName, setProjectName] = useState('')
  const [completing, setCompleting] = useState(false)

  function markComplete(s: number) {
    setCompletedSteps((prev) => new Set([...prev, s]))
    setStep(s + 1)
  }

  async function handleStep6Complete() {
    setCompleting(true)
    try {
      await authApi.completeOnboarding()
      await refreshUser()
      toast.success('Setup complete! Welcome to SEO OS.')
      navigate('/')
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setCompleting(false)
    }
  }

  const stepTitles: Record<number, string> = {
    1: 'Connect OpenAI',
    2: 'Create Your First Project',
    3: 'Connect WordPress',
    4: 'Connect Google Search Console',
    5: 'Connect Google Analytics 4',
    6: 'Set Up PageSpeed Analysis',
  }

  const stepDescs: Record<number, string> = {
    1: 'SEO OS uses OpenAI to write and optimize your content. Add your API key to get started — you pay OpenAI directly with your own key.',
    2: 'A project holds your website data, integrations, and SEO work. Enter your site details below.',
    3: 'Connect WordPress so SEO OS can read and publish content directly to your site.',
    4: 'Connect Google Search Console to see which keywords bring visitors to your site, track rankings, and detect crawl errors.',
    5: 'Connect Google Analytics 4 to see traffic trends, user behavior, and conversion data alongside your SEO metrics.',
    6: 'PageSpeed Insights measures how fast your site loads. Add a Google API key to unlock detailed performance reports in your dashboard.',
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Left sidebar */}
      <div className="hidden md:flex flex-col w-72 bg-[#0F1E36] px-8 py-10 shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-10">
          <div className="w-7 h-7 rounded-md bg-amber-500 flex items-center justify-center shrink-0">
            <span className="text-white font-bold text-sm leading-none">S</span>
          </div>
          <span className="text-white font-semibold text-base">SEO OS</span>
        </div>

        <p className="text-slate-400 text-xs uppercase tracking-widest font-semibold mb-5">Setup Wizard</p>

        <nav className="flex flex-col gap-1">
          {STEPS.map((s) => {
            const done = completedSteps.has(s.id)
            const active = step === s.id
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => done || active ? setStep(s.id) : undefined}
                className={`flex items-center gap-3 px-3 py-3 rounded-xl text-left transition-colors ${
                  active ? 'bg-white/10' : done ? 'hover:bg-white/5 cursor-pointer' : 'cursor-default opacity-50'
                }`}
              >
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-colors ${
                  done ? 'bg-amber-500 text-white' : active ? 'bg-white text-[#0F1E36]' : 'bg-white/10 text-slate-400'
                }`}>
                  {done ? (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M1.5 5L4 7.5L8.5 2.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : s.id}
                </span>
                <div className="min-w-0">
                  <p className={`text-sm font-medium truncate ${active ? 'text-white' : done ? 'text-slate-300' : 'text-slate-500'}`}>{s.title}</p>
                  <p className="text-xs text-slate-500 truncate">{s.subtitle}</p>
                </div>
              </button>
            )
          })}
        </nav>

        <div className="mt-auto">
          <div className="bg-white/5 rounded-xl p-4">
            <div className="flex justify-between text-xs text-slate-400 mb-2">
              <span>Progress</span>
              <span>{completedSteps.size} / {STEPS.length}</span>
            </div>
            <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-500 rounded-full transition-all duration-500"
                style={{ width: `${(completedSteps.size / STEPS.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Right content */}
      <div className="flex-1 flex items-start justify-center px-6 py-12 overflow-y-auto">
        <div className="w-full max-w-xl">
          {/* Mobile logo */}
          <div className="flex items-center gap-2.5 mb-8 md:hidden">
            <div className="w-7 h-7 rounded-md bg-amber-500 flex items-center justify-center shrink-0">
              <span className="text-white font-bold text-sm leading-none">S</span>
            </div>
            <span className="font-semibold text-base text-slate-900">SEO OS</span>
          </div>

          {/* Step badge */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-semibold uppercase tracking-widest text-amber-600">Step {step} of {STEPS.length}</span>
          </div>

          <h1 className="font-display text-2xl font-bold text-slate-900 mb-2">{stepTitles[step]}</h1>
          <p className="text-sm text-slate-500 leading-relaxed mb-8">{stepDescs[step]}</p>

          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            {step === 1 && <Step1 onComplete={() => markComplete(1)} />}
            {step === 2 && <Step2 onComplete={(name) => { setProjectName(name); markComplete(2) }} />}
            {step === 3 && <Step3 projectName={projectName} onComplete={() => markComplete(3)} />}
            {step === 4 && <Step4 projectName={projectName} onComplete={() => markComplete(4)} />}
            {step === 5 && <Step5 projectName={projectName} onComplete={() => markComplete(5)} />}
            {step === 6 && <Step6 onComplete={handleStep6Complete} />}
          </div>

          {/* Back button */}
          {step > 1 && (
            <button
              type="button"
              onClick={() => setStep((s) => s - 1)}
              className="mt-4 text-sm text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
            >
              ← Back to previous step
            </button>
          )}
        </div>
      </div>

      {completing && (
        <div className="fixed inset-0 bg-white/70 flex items-center justify-center z-50">
          <Loader2 size={32} className="animate-spin text-amber-500" />
        </div>
      )}
    </div>
  )
}
