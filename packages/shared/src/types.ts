// ProtoForge 前后端共享类型
// 注意:字段名以 Python 后端 (apps/api/app/schemas.py) 实际响应为准;
// 旧版 plan 的字段名若不同,这里以 backend 优先。

export type LLMProvider = 'cloud' | 'local' | 'disabled';

export type CellLine = 'HEK293' | 'HeLa' | 'Jurkat' | 'PolarYeast' | 'MarsMoss';

export type ForgeRitual = 'swift' | 'standard' | 'ancient' | 'crystal';

export type MissionLevel = 'tutorial' | 'delegation' | 'network' | 'tricky' | 'free';

export type MissionScenario = 'polar' | 'ocean' | 'soil' | 'lunar' | 'custom';

// --- Sliders / Risk ---

export interface SliderParam {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  description?: string;
}

export interface RiskRule {
  rule_id: string;
  prompt: string;
  options: string[];
  correct: string;
  explanation: string;
  severity: 'info' | 'warn' | 'block';
}

export interface Mission {
  id: string;
  title: string;
  description: string;
  scenario: MissionScenario;
  level: MissionLevel;
  target_cell_line: string;
  off_target: string;
  intron_length_range: [number, number];
  sliders: SliderParam[];
  risk_rules: RiskRule[];
  // 兼容旧字段(可选)
  slider_count?: number;
  risk_count?: number;
}

// --- Forge ---

export interface ForgeRequest {
  mission_id: string;
  params: Record<string, number>;
  generator: 'uniform' | 'preference' | 'random';
  seed?: number;
  natural_language?: string;
}

export interface ScoreVector {
  primary: number;
  components: Record<string, number>;
  weights: Record<string, number>;
}

export interface RiskFlag {
  rule_id: string;
  severity: 'info' | 'warn' | 'block';
  message: string;
}

export interface ForgeResult {
  run_id: string;
  mission_id: string;
  ritual: ForgeRitual;
  duration_ms: number;
  intron: string;
  fasta: string;
  scores: ScoreVector;
  risk_flags: RiskFlag[];
  passed_gate: boolean;
}

export interface RitualInfo {
  ritual: ForgeRitual;
  description: string;
  min_gpu_mb: number;
  models: string[];
}

// --- Risk gate ---

export interface RiskCheckRequest {
  mission_id: string;
  answers: Record<string, string>;
}

export interface RiskCheckItem {
  rule_id: string;
  user_answer: string;
  correct: boolean;
  explanation: string;
  severity: string;
}

export interface RiskCheckResponse {
  mission_id: string;
  passed: boolean;
  items: RiskCheckItem[];
  score: number;
}

// --- Gallery ---

export interface Artifact {
  id: string;
  mission_id: string;
  title: string;
  intron: string;
  fasta: string;
  scores: ScoreVector;
  ritual: ForgeRitual;
  notes?: string | null;
  risk_passed: boolean;
  created_at: string;
}

export interface ArtifactCreate {
  mission_id: string;
  title: string;
  intron: string;
  fasta: string;
  scores: ScoreVector;
  ritual: ForgeRitual;
  notes?: string | null;
  risk_passed: boolean;
}

export interface ArtifactListResponse {
  items: Artifact[];
  total: number;
}

// --- Translate ---

export interface TranslateRequest {
  mission_id: string;
  text: string;
}

export interface TranslateResponse {
  mission_id: string;
  values: Record<string, number>;
  explanation: string;
  provider: LLMProvider;
}

// --- Onboarding ---

export interface OnboardingProviderField {
  key: string;
  label: string;
  default?: string;
  secret?: boolean;
}

export interface OnboardingProvider {
  label: string;
  description: string;
  fields: OnboardingProviderField[];
}

export interface OnboardingConfig {
  name: string;
  base_url: string;
  model: string;
  api_key_set: boolean;
}

export interface OnboardingStatus {
  active: LLMProvider;
  providers: OnboardingProvider[];
  config: Record<string, OnboardingConfig>;
  last_test_at: string | null;
  last_test_ok: boolean | null;
  last_test_message: string;
}

// --- Misc ---

export interface ApiError {
  error: string;
  detail?: string;
  code?: string;
}
