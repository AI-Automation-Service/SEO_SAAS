import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { getErrorMessage } from '@/api/client'

const FEATURES = [
  'AI content writing — accepted by Google',
  'Appear on LLM search results',
  'GSC + GA4 connected out of the box',
  'Publish to WordPress, Shopify & more',
]

export function LoginPage() {
  const { login, user, isLoading } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (isLoading) return <Spinner />
  if (user) return <Navigate to="/" replace />

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex h-screen">
      <LeftPanel />
      <div className="flex-1 flex items-center justify-center bg-gray-50 px-6">
        <div className="w-full max-w-sm">
          <MobileLogo />
          <h2 className="font-display text-xl font-semibold text-slate-900 mb-1">Sign in</h2>
          <p className="text-sm text-slate-500 mb-6">Enter your credentials to continue</p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label htmlFor="email" className="block text-xs font-medium text-slate-700 mb-1.5">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className={inputCls}
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-medium text-slate-700 mb-1.5">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={inputCls}
              />
            </div>
            <button type="submit" disabled={submitting} className={btnCls}>
              {submitting ? 'Signing in...' : 'Sign in →'}
            </button>
          </form>

          <p className="text-center text-xs text-slate-400 mt-5">
            No account?{' '}
            <Link to="/register" className="text-blue-600 hover:text-blue-700 transition-colors">
              Create one for free
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

function LeftPanel() {
  return (
    <div className="hidden md:flex flex-col justify-between w-[420px] bg-[#0F1E36] px-10 py-12 shrink-0">
      <div>
        <Logo />
        <h1 className="font-display text-white text-2xl font-semibold leading-snug mb-2 mt-10">
          The AI SEO<br />Operating System
        </h1>
        <p className="text-slate-400 text-sm leading-relaxed mb-8">
          Save your money and rank your site organically.
        </p>
        <div className="flex flex-col gap-4">
          {FEATURES.map((f) => (
            <div key={f} className="flex items-start gap-3">
              <div className="mt-0.5 w-4 h-4 rounded bg-amber-500 flex items-center justify-center shrink-0">
                <Check />
              </div>
              <span className="text-slate-200 text-sm">{f}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="text-slate-600 text-xs">© 2026 SEO OS</p>
    </div>
  )
}

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-7 h-7 rounded-md bg-amber-500 flex items-center justify-center shrink-0">
        <span className="text-white font-bold text-sm leading-none">S</span>
      </div>
      <span className="text-white font-semibold text-base">SEO OS</span>
    </div>
  )
}

function MobileLogo() {
  return (
    <div className="flex items-center gap-2 mb-8 md:hidden">
      <div className="w-7 h-7 rounded-md bg-amber-500 flex items-center justify-center shrink-0">
        <span className="text-white font-bold text-sm leading-none">S</span>
      </div>
      <span className="font-semibold text-base text-slate-900">SEO OS</span>
    </div>
  )
}

function Check() {
  return (
    <svg width="9" height="9" viewBox="0 0 9 9" fill="none" aria-hidden="true">
      <path d="M1.5 4.5L3.5 6.5L7.5 2.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Spinner() {
  return (
    <div className="flex h-screen items-center justify-center bg-slate-50">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
    </div>
  )
}

const inputCls =
  'w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent transition'

const btnCls =
  'w-full py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed mt-1'
