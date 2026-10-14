/** Prop types for CouncilPanel. Matches backend/council/schemas.py contracts. */

export type Confidence = "low" | "medium" | "high";
export type ExperimentKind = "landing" | "survey" | "interview" | "offline" | "telegram";

export interface Risk {
  title: string;
  evidence: string;
  metric: string;
}

export interface CompetitorReaction {
  competitor_id: string;
  move: string;
  effect_on_share: number;
}

export interface Experiment {
  title: string;
  hypothesis: string;
  pass_threshold: string;
  kind: ExperimentKind;
}

export interface CouncilOutput {
  run_id: string;
  verdict: string;
  confidence: Confidence;
  fragility: number;
  who_buys: string[];
  who_rejects: string[];
  risks: Risk[];
  competitor_reaction: CompetitorReaction | null;
  experiments: Experiment[];
  limitations?: string[];
  engine_source?: string | null;
}

export interface KitOffline {
  flyer: string;
  checklist: string[];
  price_board_test?: string[];
}

export interface TrackingPlan {
  metrics: string[];
  decision_rule: string;
}

export interface KitAssets {
  landing_copy: string;
  survey: string[];
  interview_script: string[];
  ad_variants: string[];
  offline: KitOffline;
  telegram_variants: string[];
  tracking_plan?: TrackingPlan | null;
}

export interface KitOutput {
  hypotheses: string[];
  assets: KitAssets;
}

export interface CouncilPanelProps {
  council?: CouncilOutput | null;
  kit?: KitOutput | null;
  loading?: boolean;
  error?: string | null;
}
