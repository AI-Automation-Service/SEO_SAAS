// Project types
export interface Project {
  name: string
  cms: string
  website?: string
  business_name?: string
  business_type?: string
  country?: string
  language?: string
  tone_of_voice?: string
  target_audience?: string
  seo_goals?: string[]
  business_goals?: string[]
  competitors?: string[]
  seo_plugin?: string
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
  onboarding_complete: boolean
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

// Keyword types
export type KeywordType = 'standard' | 'question' | 'branded' | 'competitor'
export type KeywordIntent = 'informational' | 'commercial' | 'navigational' | 'transactional'
export type FunnelStage = 'tofu' | 'mofu' | 'bofu'
export type KeywordStatus = 'covered' | 'quick_win' | 'opportunity' | 'gap' | 'watch'
export type KeywordSource = 'gsc' | 'planner' | 'both' | 'manual' | 'sitemap'

export interface Keyword {
  id: number
  keyword: string
  keyword_type: KeywordType
  cluster: string | null
  is_hub: boolean
  intent: KeywordIntent | null
  funnel_stage: FunnelStage | null
  status: KeywordStatus
  action: string
  volume: number | null
  competition: number | null
  clicks: number | null
  impressions: number | null
  position: number | null
  ctr: number | null
  existing_url: string | null
  suggested_url: string | null
  snippet_opportunity: boolean
  competitor_gap: boolean
  source: KeywordSource
  page_type: string | null
  updated_at: string
}

export interface KeywordSummary {
  total: number
  covered: number
  quick_wins: number
  gaps: number
  opportunities: number
  clusters: number
  unclustered: number
}

// Knowledge Base types
export interface ProjectKnowledge {
  about: string | null
  products_services: string | null
  target_audience: string | null
  brand_voice: string | null
  competitors_notes: string | null
  seo_context: string | null
  updated_at: string | null
}

// Sitemap types
export interface SitemapSummary {
  total: number
  last_synced: string | null
}

// Strategy types
export interface StrategyResult {
  skill: string
  output: string
}

// Speed types
export interface SpeedMetric {
  display: string
  value: number | null
  score: number | null
}

export interface SpeedAuditItem {
  url?: string
  size?: string
  savings_ms?: number
}

export interface SpeedOpportunity {
  id: string
  title: string
  description: string
  display: string
  score: number
  savings_ms: number
  items: SpeedAuditItem[]
}

export interface SpeedDiagnostic {
  id: string
  title: string
  description: string
  display: string
  score: number
  items: SpeedAuditItem[]
}

export interface SpeedResult {
  url: string
  strategy: 'mobile' | 'desktop'
  performance_score: number
  metrics: {
    fcp: SpeedMetric
    lcp: SpeedMetric
    tbt: SpeedMetric
    cls: SpeedMetric
    si: SpeedMetric
    tti: SpeedMetric
  }
  opportunities: SpeedOpportunity[]
  diagnostics: SpeedDiagnostic[]
}
