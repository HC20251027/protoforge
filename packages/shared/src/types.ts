// ProtoForge 前后端共享类型

export type LLMProvider = 'cloud' | 'local' | 'disabled';

export type CellLine = 'HEK293' | 'HeLa' | 'Jurkat' | 'PolarYeast' | 'MarsMoss';

export type ForgeRitual = 'swift' | 'standard' | 'ancient' | 'crystal';

export type MissionLevel = 'tutorial' | 'commission' | 'multi-link' | 'tough' | 'free';

export interface Mission {
  id: string;
  title: string;
  scenario: 'polar' | 'mars' | 'hospital';
  level: MissionLevel;
  story_brief: string;
  task_description: string;
  proto_template: Record<string, unknown>;
  scoring: ScoringConfig;
  risk_rules: RiskRule[];
  sliders: SliderParam[];
  unlock: { min_badges: number };
  description?: string;
  slider_count?: number;
  risk_count?: number;
}

export interface ScoringConfig {
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  primary_metric: string;
}

export interface RiskRule {
  id: string;
  question: string;
  options: { value: string; label: string; correct: boolean }[];
  explanation: string;
}

export interface SliderParam {
  id: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  description: string;
}

export interface ForgeRequest {
  mission_id: string;
  params: Record<string, number>;
  generator: 'uniform' | 'preference' | 'random';
  seed?: number;
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
  scores: ScoreVector;
  fasta: string;
  risk_flags: RiskFlag[];
  proto_program: Record<string, unknown>;
  passed_gate: boolean;
}

export interface Artifact {
  id: string;
  mission_id: string;
  mission_title: string;
  created_at: string;
  scores: ScoreVector;
  fasta: string;
  passed_gate: boolean;
  ritual: ForgeRitual;
  duration_ms: number;
}

export interface TranslateRequest {
  natural_language: string;
  context?: { mission_id?: string; current_params?: Record<string, number> };
}

export interface TranslateResponse {
  params: Record<string, number>;
  generator: 'uniform' | 'preference' | 'random';
  explanation: string;
}

export interface OnboardingRequest {
  provider: LLMProvider;
  config?: {
    api_key?: string;
    base_url?: string;
    model?: string;
  };
}

export interface OnboardingResponse {
  ok: boolean;
  provider: LLMProvider;
  test_passed: boolean;
  error?: string;
}

export interface HardwareProfile {
  gpu_name: string | null;
  gpu_memory_mb: number;
  cpu_cores: number;
  ram_mb: number;
  recommended_ritual: ForgeRitual;
  recommended_models: string[];
}

export interface ApiError {
  error: string;
  detail?: string;
  code?: string;
}
