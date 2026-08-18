import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { LeadFact } from "../lib/types";

const GRADE_COLORS: Record<string, string> = {
  strong: "border-[#4eca7a] bg-[#0a1a0f] text-[#4eca7a]",
  moderate: "border-[#e7c94a] bg-[#1a1808] text-[#e7c94a]",
  weak: "border-[#e75555] bg-[#1a0808] text-[#e75555]",
};

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ["lead", id],
    queryFn: () => api.getLeadDetail(id!),
    enabled: !!id,
  });

  if (isLoading) return <div className="text-[#606078] text-sm">Loading…</div>;
  if (!data) return <div className="text-[#606078] text-sm">Lead not found.</div>;

  return (
    <div className="max-w-4xl">
      <button
        onClick={() => navigate("/leads")}
        className="text-xs text-[#4a8fe7] hover:underline mb-4 inline-block"
      >
        ← Back to leads
      </button>

      <h2 className="text-lg font-semibold mb-6">Lead Detail</h2>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <MiniStat label="Facts" value={data.fact_count} />
        <MiniStat label="Strong" value={data.strong_count} color="#4eca7a" />
        <MiniStat label="Moderate" value={data.moderate_count} color="#e7c94a" />
        <MiniStat label="Weak" value={data.weak_count} color="#e75555" />
      </div>

      {data.gap_hypothesis && (
        <div className="bg-[#0e0e16] border border-[#f0a050] rounded-lg p-5 mb-6">
          <h3 className="text-xs font-medium text-[#f0a050] uppercase tracking-wider mb-2">
            Gap Hypothesis
          </h3>
          <p className="text-sm text-[#e4e4ec] leading-relaxed">{data.gap_hypothesis.fact}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-xs text-[#606078]">
              Grade: <span className="text-[#f0a050] font-medium">{data.gap_hypothesis.grade}</span>
            </span>
            <span className="text-xs text-[#606078]">
              Corroboration: {data.gap_hypothesis.corroboration_count}
            </span>
          </div>
        </div>
      )}

      <h3 className="text-sm font-medium text-[#9898b0] mb-3 uppercase tracking-wider">Facts</h3>
      <div className="space-y-2">
        {data.facts.map((fact) => (
          <FactCard key={fact.id} fact={fact} />
        ))}
      </div>
    </div>
  );
}

function FactCard({ fact }: { fact: LeadFact }) {
  const gradeStyle = GRADE_COLORS[fact.grade || ""] || "border-[#1e1e2e] text-[#606078]";
  return (
    <div className={`bg-[#0e0e16] border rounded-lg p-4 ${fact.fact_type === "gap_hypothesis" ? "border-[#f0a050]" : "border-[#1e1e2e]"}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-[#4a8fe7] font-mono">{fact.fact_type}</span>
            <span className="text-xs text-[#606078]">Track {fact.track}</span>
          </div>
          <p className="text-sm text-[#e4e4ec] leading-relaxed">{fact.fact}</p>
          {fact.source_url && (
            <a
              href={fact.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-[#4a8fe7] hover:underline mt-1 inline-block font-mono truncate max-w-[400px]"
            >
              {fact.source_url}
            </a>
          )}
        </div>
        <div className="flex-shrink-0 flex flex-col items-end gap-1">
          {fact.grade && (
            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-mono font-medium border ${gradeStyle}`}>
              {fact.grade}
            </span>
          )}
          <span className="text-xs text-[#606078] font-mono">
            +{fact.corroboration_count}
          </span>
          {fact.recency_days !== null && (
            <span className="text-xs text-[#606078] font-mono">{fact.recency_days}d</span>
          )}
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-3">
      <div className="text-xs text-[#606078] uppercase tracking-wider mb-1">{label}</div>
      <div className="text-xl font-mono font-semibold" style={{ color: color || "#e4e4ec" }}>
        {value}
      </div>
    </div>
  );
}