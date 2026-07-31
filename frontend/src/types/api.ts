// Project types
export interface Project {
  name: string
  cms: string
  url?: string
  business_name?: string
  country?: string
  language?: string
  integrations?: ProjectIntegrations
}

export interface ProjectIntegrations {
  wordpress: WordPressConfig
  google: GoogleConfig
  shopify: ShopifyConfig
}

export interface WordPressConfig {
  enabled: boolean
  url: string
  username_env?: string
  password_env?: string
}

export interface GoogleConfig {
  enabled: boolean
  credentials_env?: string
  gsc_site_url?: string
  ga4_property_id?: string
}

export interface ShopifyConfig {
  enabled: boolean
  store_url: string
  token_env?: string
}

export interface CreateProjectRequest {
  name: string
  cms: string
}

// Integration types
export interface IntegrationStatusItem {
  name: string
  connected: boolean
  error?: string | null
}

export interface IntegrationStatusResponse {
  project: string
  integrations: IntegrationStatusItem[]
}

export interface UpdateIntegrationsConfigRequest {
  wordpress?: Partial<WordPressConfig>
  google?: Partial<GoogleConfig>
  shopify?: Partial<ShopifyConfig>
}

export interface SetSecretRequest {
  key: string
  value: string
}

export interface UploadGoogleCredentialsRequest {
  credentials_json: string
}

// Skill types
export interface Skill {
  name: string
  description?: string
}

// API error
export interface ApiError {
  detail: string | { msg: string; loc: string[] }[]
}

// Auth types
export interface AuthUser {
  id: number
  email: string
  full_name: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
}
