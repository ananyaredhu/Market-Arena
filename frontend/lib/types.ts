// Mirrors backend/common/contracts.py. Keep in sync when a contract changes (add optional fields only).

export type Role = "you" | "competitor" | "outside";

export interface Option {
  id: string;
  label: string;
  role: Role;
  price?: number;
  features?: number[];
  novelty?: number;
}

export interface Totals {
  count: number;
  share: number;
  p10: number;
  p50: number;
  p90: number;
}

export interface Choice {
  agent_id: string;
  segment: string;
  choice: string;
  prev_choice?: string | null;
  runner_up?: string | null;
  gap?: number | null;
  components: Record<string, number>;
  p_choice?: number | null;
  locked?: boolean | null;
}

export interface RunResult {
  run_id: string;
  seed: number;
  option_ids: string[];
  totals: Record<string, Totals>;
  choices: Choice[];
}

export interface Driver {
  term: string;
  delta: number;
}

export interface AgentExplain {
  agent_id: string;
  segment: string;
  choice: string;
  runner_up?: string | null;
  top_drivers: Driver[];
  narration: string;
  flip?: {
    price_drop?: number | null;
    feature_boost?: { attr: string; amount: number } | null;
    note?: string | null;
    switch_incentive?: number | null;
    price_rise?: number | null;
  } | null;
  narration_source?: string | null;
}

export interface Risk {
  title: string;
  evidence: string;
  metric: string;
}

export interface Experiment {
  title: string;
  hypothesis: string;
  pass_threshold: string;
  kind: "landing" | "survey" | "interview" | "offline" | "telegram";
}

export interface MeasuredRisk {
  title: string;
  baseline_share: number;
  perturbed_share: number;
  abs_change: number;
}

export interface MeasuredSegment {
  id: string;
  name: string;
  n: number;
  n_you: number;
  share: number;
  relationship: "buys" | "rejects";
}

export interface CouncilMeasured {
  baseline_share: number | null;
  median_share: number | null;
  p10: number | null;
  p90: number | null;
  fragility: number;
  segments: MeasuredSegment[];
  risks: MeasuredRisk[];
  competitor: {
    competitor_id: string;
    move: string;
    description?: string;
    baseline_share: number;
    candidate_share: number;
    share_change: number;
  } | null;
}

export interface CouncilOutput {
  run_id: string;
  verdict: string;
  confidence: "low" | "medium" | "high";
  fragility: number;
  who_buys: string[];
  who_rejects: string[];
  risks: Risk[];
  competitor_reaction?: { competitor_id: string; move: string; effect_on_share: number } | null;
  experiments: Experiment[];
  trend_context?: { trend: string; source_url: string; used_in: string }[] | null;
  limitations?: string[];
  engine_source?: string;
  scenario_origin?: "demo" | "stored" | "engine" | "request" | "fixture_fallback";
  project_id?: string | null;
  measured?: CouncilMeasured;
}

export interface KitOutput {
  hypotheses: string[];
  assets: {
    landing_copy: string;
    survey: string[];
    interview_script: string[];
    ad_variants: string[];
    offline?: { flyer: string; checklist: string[] } | null;
    telegram_variants: string[];
  };
}

export interface ProductProfile {
  name: string;
  description: string;
  pack: string;
  price: number;
  currency: string;
  target_customers: string[];
  features: Record<string, number>;
  geography: string;
  missing_assumptions: string[];
}

// ---------------------------------------------------------------- overrides and scenario compare (Person A)
export interface Override {
  id: string;
  project_id: string;
  type: "lock" | "edit" | "segment_tune" | "exclude";
  agent_id?: string | null;
  segment_id?: string | null;
  option_id?: string | null;
  param?: string | null;
  value?: number | null;
  factor?: number | null;
  note?: string | null;
  created_at: string;
  created_by: string;
  before?: number | null;
  after?: number | null;
  effect: string;
}

export interface OverrideResponse {
  override: Override;
  run: RunResult;
  moved: number;
  audit: string;
}

export interface AuditTrail {
  project_id: string;
  machine_generated: { agents: number; seed: number; population_source: string };
  human_adjustments: Override[];
  summary: string;
}

export interface FlipRow {
  segment: string;
  segment_name: string;
  lever: "price_cut" | "feature";
  attr: string | null;
  amount: number;
  pct: number;
  n_flipped: number;
  n_segment: number;
  text: string;
}

export interface CompareResponse {
  a: RunResult;
  b: RunResult;
  you_id: string;
  currency_symbol: string;
  period: string;
  same_seed: number;
  overrides_applied: number;
  scenarios: {
    a: { label: string; you_price: number; summary: string[] };
    b: { label: string; you_price: number; summary: string[] };
  };
  deltas: { option_id: string; label: string; share_a: number; share_b: number; delta_p50: number }[];
  headline: { delta_p50: number; range_low: number; range_high: number };
  revenue: { revenue_a: number; revenue_b: number; change_pct: number | null; note: string };
  flip_summary_b: FlipRow[];
}
