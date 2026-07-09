// ProtoForge 前后端共享类型
// 注意:字段名以 Python 后端 (apps/api/app/schemas.py) 实际响应为准;
// 旧版 plan 的字段名若不同,这里以 backend 优先。

export type LLMProvider = 'cloud' | 'local' | 'disabled';

export type CellLine = 'HEK293' | 'HeLa' | 'Jurkat' | 'PolarYeast' | 'MarsMoss';

export type ForgeRitual = 'urgent' | 'standard' | 'ancient' | 'crystal';

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
  ritual?: ForgeRitual;
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
  ritual_used: ForgeRitual;
  duration_estimate_sec: number;
  duration_ms: number;
  badge_unlocked?: string | null;
  intron: string;
  fasta: string;
  scores: ScoreVector;
  risk_flags: RiskFlag[];
  passed_gate: boolean;
  // Phase 3 Task 5:通关后 Steam Workshop 自动上传状态
  upload?: UploadStatus;
}

// --- Steam Workshop 上传 (Phase 3 Task 5) ---

export type UploadStatusKind = 'skipped' | 'queued' | 'uploaded' | 'failed';

export interface UploadStatus {
  queued: boolean;
  queue_id: string | null;
  workshop_id: string | null;
  status: UploadStatusKind;
  message: string;
}

export interface QueuedItem {
  queue_id: string;
  mission_id: string;
  ritual: ForgeRitual;
  status: string;
  workshop_id: string | null;
  error: string | null;
  attempts: number;
  enqueued_at: string;
  updated_at: string;
  export_path: string;
}

export interface QueueListResponse {
  items: QueuedItem[];
  pending_count: number;
}

export interface QueueRetryResponse {
  attempted: number;
  uploaded: number;
  failed: number;
  skipped: number;
}

export interface ExportItem {
  filename: string;
  path: string;
  size_bytes: number;
  mtime: number;
  manifest: Record<string, unknown>;
}

export interface ExportListResponse {
  items: ExportItem[];
  total: number;
}

export interface RitualInfo {
  ritual: ForgeRitual;
  description: string;
  min_gpu_mb: number;
  models: string[];
}

// --- Exit penalty (Phase 3 Task 3) ---

export type ExitOutcome = 'keep' | 'lose';

export interface UnfinishedRun {
  run_id: string;
  ritual: ForgeRitual;
  current_step: number;
  total_steps: number;
  started_at: string;
  outcome: ExitOutcome;
}

export interface ExitEvaluationRequest {
  run_id: string;
}

export interface ExitEvaluationResponse {
  outcome: ExitOutcome;
  ritual: ForgeRitual;
  progress_ratio: number;
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
