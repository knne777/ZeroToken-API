export interface ProviderAuthInfo {
  installed: boolean;
  authenticated: boolean;
  plan: string | null;
  auth_method: string | null;
  credential_path: string;
  message: string;
}

export interface AuthStatusResponse {
  codex: ProviderAuthInfo;
  agy: ProviderAuthInfo;
  claude: ProviderAuthInfo;
}

export interface ApiKeyItem {
  id: string;
  name: string;
  prefix: string;
  allowed_providers: string[];
  allowed_models: string[] | null;
  rate_limit_rpm: number;
  requests_count: number;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface AnalyticsOverview {
  total_requests: number;
  total_tokens: number;
  total_savings_usd: number;
  avg_duration_ms: number;
  providers_breakdown: { provider: string; count: number; tokens: number }[];
}

export interface RequestLogItem {
  id: string;
  api_key_name: string;
  provider: string;
  model: string;
  status_code: number;
  duration_ms: number;
  total_tokens: number;
  savings_usd: number;
  created_at: string;
}

export interface AuthSessionResponse {
  session_id: string;
  provider: string;
  status: string;
  user_code: string | null;
  verification_url: string;
  instructions: string;
}
