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
  primary_conversion?: string
  business_location?: string
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
  token_env?: string
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
  is_admin: boolean
  plan: string
}

export interface AccountUsage {
  email: string
  full_name: string
  plan: string
  max_projects: number
  project_count: number
  is_admin: boolean
}

export interface AdminUser {
  id: number
  email: string
  full_name: string
  plan: string
  max_projects: number
  is_active: boolean
  is_admin: boolean
  created_at: string
}

export interface AdminStats {
  total_users: number
  active_users: number
  admin_users: number
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
export type KeywordStatus = 'covered' | 'quick_win' | 'opportunity' | 'low_ranking' | 'gap' | 'watch'
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
  opportunities: number
  low_ranking: number
  gaps: number
  clusters: number
  unclustered: number
}

// Page Improvement types
export type PageChangeStatus = 'pending' | 'approved' | 'rolled_back' | 'no_action'
export type ActionType = 'page_edit' | 'meta_edit' | 'new_draft'
export type PlagiarismStatus = 'skipped' | 'clean' | 'flagged' | 'rewritten'

export interface PageStatistics {
  word_count?: number
  h1_count?: number
  h2_count?: number
  internal_link_count?: number
  hub_link_count?: number
  has_article_schema?: boolean
  author_visible?: boolean
  date_visible?: boolean
  keyword_frequency?: number
  images_missing_alt?: number
  current_meta_title?: string
  current_meta_description?: string
}

export interface MetaUpdates {
  plugin?: 'yoast' | 'rankmath'
  platform?: 'shopify' | 'wordpress'
  suggested_meta_title: string | null
  suggested_meta_description: string | null
}

export interface PageChange {
  id: number
  action_type: ActionType
  platform: string
  cluster_name: string
  wp_post_id: number
  wp_post_url: string
  wp_post_type: string
  change_summary: string
  changes_made: string[] | null
  statistics: PageStatistics | null
  meta_updates: MetaUpdates | null
  original_content: string
  new_content: string
  draft_title?: string | null
  draft_slug?: string | null
  draft_word_count?: number | null
  plagiarism_flag?: boolean
  plagiarism_score?: number | null
  plagiarism_status?: PlagiarismStatus
  rejection_reason?: string | null
  applied_by?: string | null
  status: PageChangeStatus
  created_at: string
  approved_at: string | null
  refresh_status?: RefreshStatus | null
}

export interface RefreshStatus {
  overall_action: string
  message: string
  days_since_last_improvement: number | null
  meta: { min_days: number; ready: boolean; days_remaining: number }
  content: { min_days: number; ready: boolean; days_remaining: number }
}

// Article writer types
export interface ArticleGenerateRequest {
  keyword: string
  cluster_name?: string
}

export interface ArticleOut {
  change_id: number
  article_job_id: string
  keyword: string
  draft_title: string
  draft_slug: string
  draft_word_count: number
  plagiarism_status: PlagiarismStatus
  plagiarism_score?: number | null
  plagiarism_flag: boolean
  content_preview: string
  status: string
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

export interface SitePage {
  id: number
  url: string
  slug: string
  page_type: string
  synced_at: string
}

// Strategy types
export interface StrategyResult {
  skill: string
  output: string
  execution_plan?: Record<string, unknown>
  change_id?: number
  queued_articles?: number
}

// API Key status
export interface KeyStatus {
  service: string
  connected: boolean
}

// Cron types
export interface CronJob {
  id: number
  job_type: string
  frequency_days: number
  enabled: boolean
  last_run_at: string | null
  next_run_at: string | null
}

export interface CronRun {
  id: number
  cron_job_id: number
  started_at: string
  completed_at: string | null
  changes_created: number
  auto_applied: number
  status: string
  error_detail: string | null
  retry_count: number
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

// Observability
export interface PlagiarismBreakdown {
  clean: number
  flagged: number
  rewritten: number
  skipped: number
}

export interface ProjectMetrics {
  ai_credits_used: number
  articles_created: number
  pages_improved: number
  changes_pending: number
  approval_rate: number
  cron_success_rate: number
  plagiarism: PlagiarismBreakdown
  period_days: number
}
