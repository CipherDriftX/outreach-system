import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import type { Lead } from "../lib/types";

const STATUS_FILTERS = ["found", "researching", "researched", "offer_drafted", "offer_approved"];

const STATUS_COLORS: Record<string, string> = {
  found: "#4a8fe7",
  researching: "#e7c94a",
  researched: "#4eca7a",
  offer_drafted: "#f0a050",
  offer_approved: "#4a8fe7",
};

export default function Leads() {
  const [status, setStatus] = useState("found");
  const navigate = useNavigate();
  const { data: leads, isLoading } = useQuery({
    queryKey: ["leads", status],
    queryFn: () => api.getLeads(status),
  });

  return (
    <div>
      <h2 className="text-lg font-semibold mb-6">Leads</h2>

      <div className="flex gap-2 mb-6">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              status === s
                ? "bg-[#1a1a28] text-[#e4e4ec]"
                : "text-[#606078] hover:text-[#9898b0]"
            }`}
          >
            {s.replace("_", " ")}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-[#606078] text-sm">Loading…</div>
      ) : !leads || leads.length === 0 ? (
        <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-8 text-center">
          <p className="text-[#606078] text-sm">No leads with status "{status}".</p>
        </div>
      ) : (
        <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1e1e2e] text-[#606078] text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3 font-medium">Company</th>
                <th className="text-left px-4 py-3 font-medium">Contact</th>
                <th className="text-left px-4 py-3 font-medium">Source</th>
                <th className="text-left px-4 py-3 font-medium">Signal</th>
                <th className="text-left px-4 py-3 font-medium">Score</th>
                <th className="text-left px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr
                  key={lead.id}
                  onClick={() => navigate(`/leads/${lead.id}`)}
                  className="border-b border-[#1a1a28] hover:bg-[#14141e] cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 text-[#e4e4ec] font-medium">
                    {lead.company_name || "—"}
                  </td>
                  <td className="px-4 py-3 text-[#9898b0]">
                    {lead.contact_name || "—"}
                    {lead.contact_email && (
                      <span className="text-[#606078] ml-2 text-xs">{lead.contact_email}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="inline-flex items-center gap-1 text-xs"
                      style={{ color: STATUS_COLORS[lead.signal_source_name] || "#606078" }}
                    >
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ backgroundColor: STATUS_COLORS[lead.signal_source_name] || "#606078" }}
                      />
                      {lead.signal_source_name}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-[#9898b0] line-clamp-1 max-w-[200px]">
                      {lead.signal_raw_text}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <ScoreBadge score={lead.signal_strength_score} />
                  </td>
                  <td className="px-4 py-3 text-xs text-[#606078] font-mono">
                    {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-[#606078]">—</span>;
  const colors: Record<number, string> = {
    0: "bg-[#1a1a28] text-[#606078]",
    1: "bg-[#1a0808] text-[#e75555]",
    2: "bg-[#1a1808] text-[#e7c94a]",
    3: "bg-[#0a1a0f] text-[#4eca7a]",
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-mono font-medium ${colors[score] || ""}`}>
      {score}
    </span>
  );
}