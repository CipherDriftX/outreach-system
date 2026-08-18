const BASE = "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
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

export const api = {
  getDashboard: () => get<import("./types").DashboardData>("/api/dashboard"),
  getSignals: (limit = 100) => get<import("./types").Signal[]>(`/api/signals?limit=${limit}`),
  getLeads: (status?: string) => get<import("./types").Lead[]>(`/api/leads${status ? `?status=${status}` : ""}`),
  getLeadDetail: (id: string) => get<import("./types").LeadDetail>(`/api/leads/${id}`),
  getLeadFacts: (id: string) => get<import("./types").LeadFact[]>(`/api/leads/${id}/facts`),
  getLeadGap: (id: string) => get<import("./types").GapHypothesis | null>(`/api/leads/${id}/gap`),
  getTemplate: () => get<import("./types").OfferTemplate>("/api/offers/template"),
  updateTemplate: (template_text: string) => put<import("./types").OfferTemplate>("/api/offers/template", { template_text }),
  getSettings: () => get<import("./types").SettingsData>("/api/settings"),
  updateGovernor: (path: string, value: unknown) => put("/api/settings/governors", { path, value }),
  health: () => get<{ status: string; store_reachable: boolean }>("/api/health"),
};