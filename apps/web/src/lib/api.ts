import type {
  Artifact,
  ArtifactCreate,
  ArtifactListResponse,
  ExitEvaluationRequest,
  ExitEvaluationResponse,
  ExportListResponse,
  ForgeRequest,
  ForgeResult,
  Mission,
  OnboardingConfig,
  OnboardingProvider,
  OnboardingStatus,
  QueueListResponse,
  QueueRetryResponse,
  RiskCheckRequest,
  RiskCheckResponse,
  RitualInfo,
  TranslateRequest,
  TranslateResponse,
  UnfinishedRun,
} from './types';

const BASE = '/api';

export class ApiException extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(typeof body === 'object' && body && 'detail' in (body as object)
      ? String((body as { detail: unknown }).detail)
      : `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiException(res.status, data);
  return data as T;
}

// --- health ---

export const healthApi = {
  get: () => request<{ status: string; version: string; data_dir: string; db_path: string; proto_profile: string }>('GET', '/health'),
};

// --- missions ---

export const missionApi = {
  list: () => request<Mission[]>('GET', '/missions'),
  get: (id: string) => request<Mission>('GET', `/missions/${id}`),
};

// --- forge ---

export const forgeApi = {
  run: (req: ForgeRequest) => request<ForgeResult>('POST', '/forge/run', req),
  listRituals: () => request<RitualInfo[]>('GET', '/forge/ritual'),
  recommendRitual: () => request<RitualInfo>('GET', '/forge/ritual/recommend'),
  // Phase 3 Task 3:退出惩罚
  unfinished: () => request<UnfinishedRun[]>('GET', '/forge/unfinished'),
  exitEvaluate: (runId: string) =>
    request<ExitEvaluationResponse>('POST', '/forge/exit-evaluate', { run_id: runId } as ExitEvaluationRequest),
};

// --- risk gate ---

export const riskApi = {
  check: (req: RiskCheckRequest) => request<RiskCheckResponse>('POST', '/risk/check', req),
};

// --- gallery ---

export const galleryApi = {
  list: () => request<ArtifactListResponse>('GET', '/gallery'),
  create: (body: ArtifactCreate) => request<Artifact>('POST', '/gallery', body),
  get: (id: string) => request<Artifact>('GET', `/gallery/${id}`),
};

// --- onboarding ---

export type LLMProviderV2 = 'cloud' | 'local-bundled' | 'disabled';
export type CloudProvider = 'deepseek' | 'claude' | 'openai';

export interface OnboardingState {
  completed: boolean;
  llm_provider: LLMProviderV2;
  cloud_provider: CloudProvider | null;
  has_api_key: boolean;
  vendor_status: {
    proto_language?: VendorResourceStatus;
    ml_models?: Record<string, VendorResourceStatus>;
    local_llm?: VendorResourceStatus;
    error?: string;
  };
}

export interface OnboardingSubmission {
  llm_provider: LLMProviderV2;
  cloud_provider?: CloudProvider | null;
  api_key?: string | null;
}

export interface OnboardingCompleteResponse {
  ok: boolean;
  message: string;
}

export const onboardingApi = {
  status: () => request<OnboardingStatus>('GET', '/onboarding/status'),
  test: (name: string, config: Record<string, string>) =>
    request<{ ok: boolean; message: string; tested_at: string }>('POST', '/onboarding/test', { name, config }),
  save: (active: string, providers: Record<string, Record<string, string>>) =>
    request<OnboardingStatus>('POST', '/onboarding/save', { active, providers }),
  reset: () => request<OnboardingStatus>('POST', '/onboarding/reset'),
  // Phase 3 Task 4: 引导页 3 步配置 + 持久化
  getState: (userId: string) =>
    request<OnboardingState>('GET', `/onboarding/state?user_id=${encodeURIComponent(userId)}`),
  complete: (userId: string, sub: OnboardingSubmission) =>
    request<OnboardingCompleteResponse>('POST', `/onboarding/complete?user_id=${encodeURIComponent(userId)}`, sub),
};

// --- vendor (Phase 3 Task 1.5) ---

export interface VendorResourceStatus {
  available: boolean;
  size_mb: number;
  path: string;
  model_name?: string;
}

export interface VendorStatus {
  proto_language: VendorResourceStatus;
  ml_models: Record<string, VendorResourceStatus>;
  local_llm: VendorResourceStatus;
}

export const vendorApi = {
  status: () => request<VendorStatus>('GET', '/vendor/status'),
};

// --- translate ---

export const translateApi = {
  run: (req: TranslateRequest) => request<TranslateResponse>('POST', '/translate', req),
};

// --- protoforge (Phase 3 Task 5: Steam 创意工坊上传) ---

export const protoforgeApi = {
  // 上传队列
  queue: (playerId: string) =>
    request<QueueListResponse>('GET', `/protoforge/queue?player_id=${encodeURIComponent(playerId)}`),
  retry: (playerId: string) =>
    request<QueueRetryResponse>('POST', `/protoforge/queue/retry?player_id=${encodeURIComponent(playerId)}`),
  cancel: (playerId: string, queueId: string) =>
    request<{ ok: boolean; queue_id: string }>(
      'POST',
      `/protoforge/queue/${encodeURIComponent(queueId)}/cancel`,
      { player_id: playerId },
    ),
  // 导出文件
  exports: (playerId: string) =>
    request<ExportListResponse>('GET', `/protoforge/exports?player_id=${encodeURIComponent(playerId)}`),
};

export type { OnboardingProvider, OnboardingConfig };
