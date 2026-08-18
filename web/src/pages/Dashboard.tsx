import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.getDashboard,
  });

  if (isLoading) return <div className="text-[#606078] text-sm">Loading…</div>;

  const p = data?.pipeline;
  const stages = [
    { key: "found", label: "Found" },
    { key: "researching", label: "Researching" },
    { key: "researched", label: "Researched" },
    { key: "offer_drafted", label: "Offers Drafted" },
    { key: "offer_approved", label: "Approved" },
  ];

  return (
    <div className="max-w-4xl">
      <h2 className="text-lg font-semibold mb-6">Dashboard</h2>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Signals" value={p?.total_signals ?? 0} />
        <StatCard label="Leads" value={p?.total_leads ?? 0} />
        <StatCard label="Researched" value={p?.researched ?? 0} />
        <StatCard label="Offers Ready" value={p?.offer_drafted ?? 0} />
      </div>

      <h3 className="text-sm font-medium text-[#9898b0] mb-3 uppercase tracking-wider">
        Pipeline
      </h3>
      <div className="flex items-center gap-1 mb-8">
        {stages.map(({ key, label }, i) => {
          const count = (p as Record<string, number> | undefined)?.[key] ?? 0;
          const max = Math.max(...stages.map((s) => (p as Record<string, number> | undefined)?.[s.key] ?? 0), 1);
          const width = (count / max) * 100;
          return (
            <div key={key} className="flex-1">
              <div className="text-xs text-[#9898b0] mb-1 text-center">{label}</div>
              <div className="h-2 bg-[#14141e] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#4a8fe7] rounded-full transition-all"
                  style={{ width: `${Math.max(width, 3)}%` }}
                />
              </div>
              <div className="text-xs font-mono text-[#e4e4ec] mt-1 text-center">
                {count}
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-6">
        <h3 className="text-sm font-medium text-[#9898b0] mb-3 uppercase tracking-wider">
          Status
        </h3>
        <p className="text-sm text-[#9898b0]">
          The research system is idle. Start a signal discovery run to begin
          finding leads, or configure signal source adapters in Settings.
        </p>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-4">
      <div className="text-xs text-[#606078] uppercase tracking-wider mb-1">{label}</div>
      <div className="text-2xl font-mono font-semibold text-[#e4e4ec]">{value}</div>
    </div>
  );
}