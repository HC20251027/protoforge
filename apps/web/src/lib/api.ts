import type {
  Artifact,
  ArtifactCreate,
  ArtifactListResponse,
  ForgeRequest,
  ForgeResult,
  Mission,
  OnboardingConfig,
  OnboardingProvider,
  OnboardingStatus,
  RiskCheckRequest,
  RiskCheckResponse,
  RitualInfo,
  TranslateRequest,
  TranslateResponse,
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

export const onboardingApi = {
  status: () => request<OnboardingStatus>('GET', '/onboarding/status'),
  test: (name: string, config: Record<string, string>) =>
    request<{ ok: boolean; message: string; tested_at: string }>('POST', '/onboarding/test', { name, config }),
  save: (active: string, providers: Record<string, Record<string, string>>) =>
    request<OnboardingStatus>('POST', '/onboarding/save', { active, providers }),
  reset: () => request<OnboardingStatus>('POST', '/onboarding/reset'),
};

// --- translate ---

export const translateApi = {
  run: (req: TranslateRequest) => request<TranslateResponse>('POST', '/translate', req),
};

export type { OnboardingProvider, OnboardingConfig };
