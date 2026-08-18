const BASE = "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export interface RunInfo {
  run_id: string;
  thread_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  phase: string;
  error: string | null;
  summary?: {
    signals_discovered: number;
    leads_created: number;
    errors: number;
  };
}

export interface Offer {
  id: string;
  lead_id: string;
  subject: string;
  body?: string;
  unresolved_placeholders: string[];
  status: string;
  created_at: string | null;
  company_name: string | null;
  contact_name: string | null;
  contact_email: string | null;
  resolved_fact_ids?: string[];
}

export const api = {
  getDashboard: () => get<import("./types").DashboardData>("/api/dashboard"),
  getSignals: (limit = 100) => get<import("./types").Signal[]>(`/api/signals?limit=${limit}`),
  getAdapters: () => get<{ name: string; source_type: string }[]>("/api/signals/adapters"),
  getLeads: (status?: string) => get<import("./types").Lead[]>(`/api/leads${status ? `?status=${status}` : ""}`),
  getLeadDetail: (id: string) => get<import("./types").LeadDetail>(`/api/leads/${id}`),
  getLeadFacts: (id: string) => get<import("./types").LeadFact[]>(`/api/leads/${id}/facts`),
  getLeadGap: (id: string) => get<import("./types").GapHypothesis | null>(`/api/leads/${id}/gap`),
  getTemplate: () => get<import("./types").OfferTemplate>("/api/offers/template"),
  updateTemplate: (template_text: string) => put<import("./types").OfferTemplate>("/api/offers/template", { template_text }),
  getTemplatePlaceholders: () => get<{ fact_placeholders: string[]; signal_placeholders: string[]; conditionals: string[] }>("/api/offers/template/placeholders"),
  getOffers: () => get<Offer[]>("/api/offers"),
  getOffer: (id: string) => get<Offer>(`/api/offers/${id}`),
  generateOffer: (leadId: string) => post<{ offer_id: string; subject: string; body: string; fully_resolved: boolean; unresolved_placeholders: string[] }>(`/api/offers/generate/${leadId}`),
  generateAllOffers: () => post<{ generated: number; total: number }>("/api/offers/generate-all"),
  getRuns: () => get<RunInfo[]>("/api/runs"),
  launchRun: (icp_root?: string) => post<{ run_id: string; thread_id: string; status: string }>("/api/runs", { icp_root }),
  getRun: (id: string) => get<RunInfo>(`/api/runs/${id}`),
  getRunLogs: (id: string, since = 0) => get<{ entries: any[]; cursor: number }>(`/api/runs/${id}/logs?since=${since}`),
  runResearch: () => post<{ job_id?: string; total?: number; status: string; message?: string }>("/api/research/run"),
  getSettings: () => get<import("./types").SettingsData>("/api/settings"),
  updateGovernor: (path: string, value: unknown) => put("/api/settings/governors", { path, value }),
  health: () => get<{ status: string; store_reachable: boolean }>("/api/health"),
};