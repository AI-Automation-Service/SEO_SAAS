import axios, { AxiosError } from 'axios'
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
} from '@/types/api'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// Extracts a human-readable error message from any Axios error
export function getErrorMessage(err: unknown): string {
  const error = err as AxiosError<ApiError>
  const detail = error.response?.data?.detail
  if (!detail) return error.message || 'An unexpected error occurred'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ')
  return 'An unexpected error occurred'
}

// Projects
export const projectsApi = {
  list: () => api.get<Project[]>('/api/projects').then((r) => r.data),
  get: (name: string) => api.get<Project>(`/api/projects/${name}`).then((r) => r.data),
  create: (body: CreateProjectRequest) =>
    api.post<Project>('/api/projects', body).then((r) => r.data),
  validate: (name: string) =>
    api.get<{ valid: boolean; errors: string[] }>(`/api/projects/${name}/validate`).then((r) => r.data),
}

// Integrations
export const integrationsApi = {
  status: (name: string) =>
    api.get<IntegrationStatusResponse>(`/api/projects/${name}/integrations/status`).then((r) => r.data),
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

// Skills
export const skillsApi = {
  list: () => api.get<Skill[]>('/api/skills').then((r) => r.data),
}

// Health
export const healthApi = {
  check: () => api.get<{ status: string; service: string }>('/health').then((r) => r.data),
}
