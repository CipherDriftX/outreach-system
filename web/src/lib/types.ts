// Shared TypeScript types matching the backend API shapes

export interface Signal {
  id: string;
  source_type: string;
  source_name: string;
  url: string;
  author_handle: string | null;
  raw_text: string;
  matched_pattern: string | null;
  posted_at: string | null;
  captured_at: string | null;
  lead_id: string | null;
  lead_status: string | null;
}

export interface Lead {
  id: string;
  company_name: string | null;
  contact_name: string | null;
  contact_email: string | null;
  status: string;
  signal_strength_score: number | null;
  origin_signal_id: string;
  created_at: string | null;
  signal_raw_text: string;
  signal_source_type: string;
  signal_source_name: string;
  signal_url: string;
}

export interface LeadFact {
  id: string;
  fact_type: string;
  track: string;
  fact: string;
  source_url: string | null;
  observed_at: string | null;
  corroboration_count: number;
  consistency: number | null;
  recency_days: number | null;
  effect_size: number | null;
  grade: "strong" | "moderate" | "weak" | null;
}

export interface GapHypothesis {
  id: string;
  fact: string;
  grade: string;
  source_url: string | null;
  corroboration_count: number;
}

export interface LeadDetail {
  lead_id: string;
  facts: LeadFact[];
  gap_hypothesis: GapHypothesis | null;
  fact_count: number;
  strong_count: number;
  moderate_count: number;
  weak_count: number;
}

export interface OfferTemplate {
  id: string | null;
  name: string;
  template_text: string;
  updated_at: string | null;
}

export interface PipelineStats {
  found: number;
  researching: number;
  researched: number;
  offer_drafted: number;
  offer_approved: number;
  total_signals: number;
  total_leads: number;
}

export interface DashboardData {
  pipeline: PipelineStats;
  business_id: string;
}

export interface SettingsData {
  business_id: string | null;
  governors: Record<string, unknown>;
}