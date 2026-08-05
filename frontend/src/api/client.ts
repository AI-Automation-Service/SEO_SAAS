import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type {
  Project,
  CreateProjectRequest,
  IntegrationStatusResponse,
  IntegrationStatusItem,
  UpdateIntegrationsConfigRequest,
  SetSecretRequest,
  UploadGoogleCredentialsRequest,
  Skill,
  ApiError,
  AuthUser,
  TokenResponse,
  LoginRequest,
  RegisterRequest,
  Keyword,
  KeywordSummary,
  ProjectKnowledge,
  SitemapSummary,
  SitePage,
  StrategyResult,
  SpeedResult,
  PageChange,
  ArticleGenerateRequest,
  ArticleOut,
  KeyStatus,
  CronJob,
  CronRun,
  AccountUsage,
  AdminUser,
  AdminStats,
  ProjectMetrics,
} from '@/types/api'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// Bare client for refresh — no interceptors to prevent recursive 401 loops
const refreshClient = axios.create({ baseURL: API_BASE })

// ── Request interceptor — attach token ───────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor — silent token refresh on 401 ──────────────────────
type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean }

let isRefreshing = false
let queue: Array<{ resolve: (t: string) => void; reject: (e: unknown) => void }> = []

function flushQueue(error: unknown, token: string | null) {
  queue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token!)))
  queue = []
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const cfg = error.config as RetryConfig | undefined
    if (error.response?.status !== 401 || cfg?._retry) return Promise.reject(error)

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => queue.push({ resolve, reject })).then(
        (token) => {
          cfg!.headers!.Authorization = `Bearer ${token}`
          return api(cfg!)
        },
      )
    }

    cfg!._retry = true
    isRefreshing = true
    const rt = localStorage.getItem('refresh_token')

    if (!rt) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    try {
      const { data } = await refreshClient.post<TokenResponse>('/api/auth/refresh', {
        refresh_token: rt,
      })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      flushQueue(null, data.access_token)
      cfg!.headers!.Authorization = `Bearer ${data.access_token}`
      return api(cfg!)
    } catch (err) {
      flushQueue(err, null)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
      return Promise.reject(err)
    } finally {
      isRefreshing = false
    }
  },
)

// ── Error helper ─────────────────────────────────────────────────────────────
export function getErrorMessage(err: unknown): string {
  const error = err as AxiosError<ApiError>
  const detail = error.response?.data?.detail
  if (!detail) return error.message || 'An unexpected error occurred'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ')
  return 'An unexpected error occurred'
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (body: LoginRequest) =>
    api.post<TokenResponse>('/api/auth/login', body).then((r) => r.data),
  register: (body: RegisterRequest) =>
    api.post<TokenResponse>('/api/auth/register', body).then((r) => r.data),
  me: () => api.get<AuthUser>('/api/auth/me').then((r) => r.data),
  completeOnboarding: () => api.post('/api/auth/complete-onboarding').then((r) => r.data),
}

// ── API Key management ────────────────────────────────────────────────────────
export const keysApi = {
  list: () => api.get<KeyStatus[]>('/api/keys').then((r) => r.data),
  save: (service: string, value: string) =>
    api.put(`/api/keys/${service}`, { value }).then((r) => r.data),
  test: (service: string, value: string) =>
    api.post('/api/keys/test', { service, value }).then((r) => r.data),
  delete: (service: string) =>
    api.delete(`/api/keys/${service}`).then((r) => r.data),
}

// ── Projects ─────────────────────────────────────────────────────────────────
export const projectsApi = {
  list: () => api.get<Project[]>('/api/projects').then((r) => r.data),
  get: (name: string) => api.get<Project>(`/api/projects/${name}`).then((r) => r.data),
  create: (body: CreateProjectRequest) =>
    api.post<Project>('/api/projects', body).then((r) => r.data),
  update: (name: string, body: Partial<Pick<Project, 'website' | 'business_name' | 'business_type' | 'country' | 'language' | 'tone_of_voice' | 'target_audience' | 'seo_goals' | 'business_goals' | 'competitors' | 'seo_plugin' | 'primary_conversion' | 'business_location'>>) =>
    api.patch(`/api/projects/${name}`, body).then((r) => r.data),
  delete: (name: string) =>
    api.delete(`/api/projects/${name}`).then((r) => r.data),
  validate: (name: string) =>
    api
      .get<{ valid: boolean; errors: string[] }>(`/api/projects/${name}/validate`)
      .then((r) => r.data),
}

// ── Integrations ─────────────────────────────────────────────────────────────
export const integrationsApi = {
  status: (name: string) =>
    api
      .get<IntegrationStatusResponse>(`/api/projects/${name}/integrations/status`)
      .then((r) => r.data),
  test: (name: string, integration: string) =>
    api
      .post<IntegrationStatusItem>(`/api/projects/${name}/integrations/test/${integration}`)
      .then((r) => r.data),
  updateConfig: (name: string, body: UpdateIntegrationsConfigRequest) =>
    api.patch(`/api/projects/${name}/integrations/config`, body).then((r) => r.data),
  setSecret: (name: string, body: SetSecretRequest) =>
    api.post(`/api/projects/${name}/integrations/secrets`, body).then((r) => r.data),
  uploadGoogleCredentials: (name: string, body: UploadGoogleCredentialsRequest) =>
    api
      .post(`/api/projects/${name}/integrations/secrets/google-credentials`, body)
      .then((r) => r.data),
}

// ── Skills ────────────────────────────────────────────────────────────────────
export const skillsApi = {
  list: () => api.get<Skill[]>('/api/skills').then((r) => r.data),
}

// ── Keywords ──────────────────────────────────────────────────────────────────
export const keywordsApi = {
  summary: (name: string) =>
    api.get<KeywordSummary>(`/api/projects/${name}/keywords/summary`).then((r) => r.data),

  list: (name: string, params?: Record<string, string>) =>
    api.get<Keyword[]>(`/api/projects/${name}/keywords`, { params }).then((r) => r.data),

  sync: (name: string) =>
    api.post<{ synced: number; message: string }>(`/api/projects/${name}/keywords/sync`).then((r) => r.data),

  upload: (name: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    // Do NOT set Content-Type — browser must set it with the multipart boundary
    return api.post<{ imported: number; message: string }>(
      `/api/projects/${name}/keywords/upload`,
      form,
    ).then((r) => r.data)
  },

  cluster: (name: string) =>
    api.post<{ clustered: number; clusters: number; message: string }>(
      `/api/projects/${name}/keywords/cluster`,
    ).then((r) => r.data),

  update: (name: string, id: number, body: Partial<Keyword>) =>
    api.patch<Keyword>(`/api/projects/${name}/keywords/${id}`, body).then((r) => r.data),

  remove: (name: string, id: number) =>
    api.delete(`/api/projects/${name}/keywords/${id}`).then((r) => r.data),

  reset: (name: string) =>
    api.delete<{ deleted: number; message: string }>(`/api/projects/${name}/keywords`).then((r) => r.data),

  reclassify: (name: string) =>
    api.post<{ updated: number }>(`/api/projects/${name}/keywords/reclassify`).then((r) => r.data),
}

// ── Sitemap ───────────────────────────────────────────────────────────────────
export const sitemapApi = {
  summary: (name: string) =>
    api.get<SitemapSummary>(`/api/projects/${name}/sitemap/summary`).then((r) => r.data),
  sync: (name: string) =>
    api.post<{ synced: number; message: string }>(`/api/projects/${name}/sitemap/sync`).then((r) => r.data),
  pages: (name: string) =>
    api.get<SitePage[]>(`/api/projects/${name}/sitemap/pages`).then((r) => r.data),
}

// ── Strategy ──────────────────────────────────────────────────────────────────
export const strategyApi = {
  plan: (name: string) =>
    api.post<StrategyResult>(`/api/projects/${name}/strategy/plan`).then((r) => r.data),

  content: (name: string) =>
    api.post<StrategyResult>(`/api/projects/${name}/strategy/content`).then((r) => r.data),

  architecture: (name: string) =>
    api.post<StrategyResult>(`/api/projects/${name}/strategy/architecture`).then((r) => r.data),

  flow: (name: string, keywordId: number) =>
    api.post<StrategyResult>(`/api/projects/${name}/strategy/flow/${keywordId}`).then((r) => r.data),

  competitorPage: (name: string, competitorUrl: string) =>
    api
      .post<StrategyResult>(`/api/projects/${name}/strategy/competitor-page`, {
        competitor_url: competitorUrl,
      })
      .then((r) => r.data),

  improvePage: (name: string, keywordId: number) =>
    api
      .post<StrategyResult>(`/api/projects/${name}/strategy/improve-page/${keywordId}`)
      .then((r) => r.data),

  savedOutputs: (name: string) =>
    api.get<Record<string, string>>(`/api/projects/${name}/strategy/saved`).then((r) => r.data),

  updateOutput: (name: string, type: string, output: string) =>
    api
      .put<StrategyResult>(`/api/projects/${name}/strategy/saved/${encodeURIComponent(type)}`, { output })
      .then((r) => r.data),

  deleteOutput: (name: string, type: string) =>
    api.delete(`/api/projects/${name}/strategy/saved/${encodeURIComponent(type)}`).then((r) => r.data),

  publishCompetitor: (name: string, competitorUrl: string) =>
    api
      .post<{ id: number; url: string; title: string; status: string }>(
        `/api/projects/${name}/strategy/publish-competitor`,
        { competitor_url: competitorUrl },
      )
      .then((r) => r.data),
}

// ── Speed ─────────────────────────────────────────────────────────────────────
export const speedApi = {
  get: (name: string, strategy: 'mobile' | 'desktop' = 'mobile') =>
    api
      .get<SpeedResult>(`/api/projects/${name}/speed`, { params: { strategy } })
      .then((r) => r.data),
}

// ── Knowledge Base ────────────────────────────────────────────────────────────
export const knowledgeApi = {
  get: (name: string) =>
    api.get<ProjectKnowledge>(`/api/projects/${name}/knowledge`).then((r) => r.data),
  save: (name: string, body: Omit<ProjectKnowledge, 'updated_at'>) =>
    api.put<ProjectKnowledge>(`/api/projects/${name}/knowledge`, body).then((r) => r.data),
}

// ── Page Improvement ──────────────────────────────────────────────────────────
function makeImproveApi(segment: string) {
  return {
    analyze: (name: string, cluster_name: string) =>
      api.post<PageChange[]>(`/api/projects/${name}/${segment}/analyze`, { cluster_name }).then((r) => r.data),
    apply: (name: string, changeId: number, contentOverride?: string) =>
      api.post<PageChange>(
        `/api/projects/${name}/${segment}/apply/${changeId}`,
        contentOverride ? { content_override: contentOverride } : undefined,
      ).then((r) => r.data),
    rollback: (name: string, changeId: number) =>
      api.post<PageChange>(`/api/projects/${name}/${segment}/rollback/${changeId}`).then((r) => r.data),
    history: (name: string) =>
      api.get<PageChange[]>(`/api/projects/${name}/${segment}/history`).then((r) => r.data),
  }
}

export const improveApi = makeImproveApi('improve')

// ── Article Writer ────────────────────────────────────────────────────────────
export const articleApi = {
  generate: (name: string, body: ArticleGenerateRequest) =>
    api.post<ArticleOut>(`/api/projects/${name}/article/generate`, body).then((r) => r.data),
}

// ── Cron jobs ─────────────────────────────────────────────────────────────────
export const cronApi = {
  list: (name: string) =>
    api.get<CronJob[]>(`/api/projects/${name}/cron`).then((r) => r.data),
  upsert: (name: string, body: { job_type: string; frequency_days?: number; enabled: boolean }) =>
    api.post<CronJob>(`/api/projects/${name}/cron`, body).then((r) => r.data),
  update: (name: string, jobType: string, body: { enabled?: boolean; frequency_days?: number }) =>
    api.put<CronJob>(`/api/projects/${name}/cron/${jobType}`, body).then((r) => r.data),
  runs: (name: string) =>
    api.get<CronRun[]>(`/api/projects/${name}/cron/runs`).then((r) => r.data),
  runNow: (name: string, jobType: string) =>
    api.post<{ message: string }>(`/api/projects/${name}/cron/${jobType}/run-now`).then((r) => r.data),
}

// ── Feedback ──────────────────────────────────────────────────────────────────
export const feedbackApi = {
  submit: (name: string, changeId: number, verdict: 'approve' | 'reject', comment?: string) =>
    api
      .post(`/api/projects/${name}/improve/feedback/${changeId}`, { verdict, comment })
      .then((r) => r.data),
  preferences: (name: string) =>
    api.get<{ rules: string[]; updated_at: string | null }>(`/api/projects/${name}/improve/preferences`).then((r) => r.data),
  refreshPreferences: (name: string) =>
    api.post<{ rules: string[]; updated_at: string | null }>(`/api/projects/${name}/improve/preferences/refresh`).then((r) => r.data),
}

// ── Shopify Improve ───────────────────────────────────────────────────────────
export const shopifyImproveApi = makeImproveApi('shopify/improve')

// ── Account ───────────────────────────────────────────────────────────────────
export const accountApi = {
  usage: () => api.get<AccountUsage>('/api/account/usage').then((r) => r.data),
  changePassword: (current_password: string, new_password: string) =>
    api.put('/api/account/password', { current_password, new_password }).then((r) => r.data),
  deleteAccount: () => api.delete('/api/account').then((r) => r.data),
}

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminApi = {
  users: () => api.get<AdminUser[]>('/api/admin/users').then((r) => r.data),
  stats: () => api.get<AdminStats>('/api/admin/stats').then((r) => r.data),
  updatePlan: (userId: number, plan: string) =>
    api.put(`/api/admin/users/${userId}/plan`, { plan }).then((r) => r.data),
  deleteUser: (userId: number) =>
    api.delete(`/api/admin/users/${userId}`).then((r) => r.data),
}

// ── OAuth flows (Phase 3) ─────────────────────────────────────────────────────
export const oauthApi = {
  googleStart: () =>
    api.get<{ url: string }>('/api/oauth/google/start').then((r) => r.data),
  googleCallback: (code: string) =>
    api.post<{ ok: boolean }>('/api/oauth/google/callback', { code }).then((r) => r.data),
  shopifyStart: (name: string, shop: string) =>
    api
      .get<{ url: string }>(`/api/projects/${name}/oauth/shopify/start`, { params: { shop } })
      .then((r) => r.data),
}

// ── Observability ─────────────────────────────────────────────────────────────
export const metricsApi = {
  get: (name: string, period_days = 30) =>
    api
      .get<ProjectMetrics>(`/api/projects/${name}/metrics`, { params: { period_days } })
      .then((r) => r.data),
}

// ── Health ────────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () =>
    api.get<{ status: string; service: string }>('/health').then((r) => r.data),
}
