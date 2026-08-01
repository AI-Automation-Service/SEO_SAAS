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
  SitemapSummary,
  StrategyResult,
  SpeedResult,
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
  save: (service: string, value: string) =>
    api.put(`/api/keys/${service}`, { value }).then((r) => r.data),
  test: (service: string, value: string) =>
    api.post('/api/keys/test', { service, value }).then((r) => r.data),
}

// ── Projects ─────────────────────────────────────────────────────────────────
export const projectsApi = {
  list: () => api.get<Project[]>('/api/projects').then((r) => r.data),
  get: (name: string) => api.get<Project>(`/api/projects/${name}`).then((r) => r.data),
  create: (body: CreateProjectRequest) =>
    api.post<Project>('/api/projects', body).then((r) => r.data),
  update: (name: string, body: { website: string }) =>
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
}

// ── Sitemap ───────────────────────────────────────────────────────────────────
export const sitemapApi = {
  summary: (name: string) =>
    api.get<SitemapSummary>(`/api/projects/${name}/sitemap/summary`).then((r) => r.data),
  sync: (name: string) =>
    api.post<{ synced: number; message: string }>(`/api/projects/${name}/sitemap/sync`).then((r) => r.data),
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
}

// ── Speed ─────────────────────────────────────────────────────────────────────
export const speedApi = {
  get: (name: string, strategy: 'mobile' | 'desktop' = 'mobile') =>
    api
      .get<SpeedResult>(`/api/projects/${name}/speed`, { params: { strategy } })
      .then((r) => r.data),
}

// ── Health ────────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () =>
    api.get<{ status: string; service: string }>('/health').then((r) => r.data),
}
