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
}

// ── Projects ─────────────────────────────────────────────────────────────────
export const projectsApi = {
  list: () => api.get<Project[]>('/api/projects').then((r) => r.data),
  get: (name: string) => api.get<Project>(`/api/projects/${name}`).then((r) => r.data),
  create: (body: CreateProjectRequest) =>
    api.post<Project>('/api/projects', body).then((r) => r.data),
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
