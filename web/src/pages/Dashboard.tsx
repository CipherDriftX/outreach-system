import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.getDashboard,
  });

  const { data: runs } = useQuery({
    queryKey: ["runs"],
    queryFn: api.getRuns,
    refetchInterval: 3000,
  });

  const launchMutation = useMutation({
    mutationFn: () => api.launchRun(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const researchMutation = useMutation({
    mutationFn: () => api.runResearch(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const offersMutation = useMutation({
    mutationFn: () => api.generateAllOffers(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offers"] });
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  if (isLoading) return <div className="text-[#606078] text-sm">Loading…</div>;

  const p = data?.pipeline;
  const stages = [
    { key: "found", label: "Found" },
    { key: "researching", label: "Researching" },
    { key: "researched", label: "Researched" },
    { key: "offer_drafted", label: "Offers Ready" },
  ];
  const counts = stages.map((s) => (p as Record<string, number> | undefined)?.[s.key] ?? 0);
  const max = Math.max(...counts, 1);

  const activeRuns = runs?.filter((r) => r.status === "running") ?? [];
  const lastRun = runs?.filter((r) => r.status === "completed")[0];

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold">Dashboard</h2>
        <div className="flex gap-2">
          <button
            onClick={() => launchMutation.mutate()}
            disabled={launchMutation.isPending || activeRuns.length > 0}
            className="px-3 py-2 bg-[#4a8fe7] text-white text-xs font-medium rounded-lg hover:bg-[#3a7fd7] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {launchMutation.isPending ? "Starting…" : "⚡ Start Signal Discovery"}
          </button>
          <button
            onClick={() => researchMutation.mutate()}
            disabled={researchMutation.isPending}
            className="px-3 py-2 bg-[#0e0e16] border border-[#2a2a3a] text-[#e4e4ec] text-xs font-medium rounded-lg hover:bg-[#14141e] transition-colors disabled:opacity-50"
          >
            {researchMutation.isPending ? "Researching…" : "◆ Research Leads"}
          </button>
          <button
            onClick={() => offersMutation.mutate()}
            disabled={offersMutation.isPending}
            className="px-3 py-2 bg-[#0e0e16] border border-[#2a2a3a] text-[#e4e4ec] text-xs font-medium rounded-lg hover:bg-[#14141e] transition-colors disabled:opacity-50"
          >
            {offersMutation.isPending ? "Building…" : "✧ Generate Offers"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-[#1a0808] border border-[#e75555] text-[#e75555] text-xs rounded-lg p-3 mb-4">
          {error}
        </div>
      )}

      {activeRuns.length > 0 && (
        <div className="bg-[#0e0e16] border border-[#4a8fe7] rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#4a8fe7] animate-pulse" />
            <span className="text-sm text-[#e4e4ec] font-medium">
              Signal discovery running
            </span>
            <span className="text-xs text-[#606078] font-mono ml-2">
              phase: {activeRuns[0]?.phase || "starting"}
            </span>
          </div>
        </div>
      )}

      {lastRun && lastRun.summary && (
        <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-4 mb-6">
          <span className="text-xs text-[#9898b0] uppercase tracking-wider">
            Last run
          </span>
          <div className="flex gap-6 mt-2 text-sm">
            <span className="text-[#e4e4ec]">
              {lastRun.summary.signals_discovered}{" "}
              <span className="text-[#606078] text-xs">signals</span>
            </span>
            <span className="text-[#e4e4ec]">
              {lastRun.summary.leads_created}{" "}
              <span className="text-[#606078] text-xs">leads</span>
            </span>
            <span className="text-[#606078] text-xs">
              {lastRun.summary.errors} errors
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Signals" value={p?.total_signals ?? 0} />
        <StatCard label="Leads" value={p?.total_leads ?? 0} />
        <StatCard label="Researched" value={p?.researched ?? 0} />
        <StatCard label="Offers" value={p?.offer_drafted ?? 0} />
      </div>

      <h3 className="text-sm font-medium text-[#9898b0] mb-3 uppercase tracking-wider">
        Pipeline
      </h3>
      <div className="flex items-start gap-1 mb-8">
        {stages.map(({ key, label }, i) => {
          const count = (p as Record<string, number> | undefined)?.[key] ?? 0;
          const width = (count / max) * 100;
          return (
            <div key={key} className="flex-1">
              <div className="text-xs text-[#9898b0] mb-1 text-center">{label}</div>
              <div className="h-2 bg-[#14141e] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#4a8fe7] rounded-full transition-all duration-500"
                  style={{ width: `${Math.max(width, count > 0 ? 4 : 0)}%` }}
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
          How it works
        </h3>
        <ol className="space-y-2 text-sm text-[#9898b0] list-decimal list-inside">
          <li>
            <span className="text-[#e4e4ec]">Start Signal Discovery</span> — the
            research graph searches the internet for publicly expressed needs
          </li>
          <li>
            <span className="text-[#e4e4ec]">Research Leads</span> — each
            triaged lead gets deep multi-dimensional research
          </li>
          <li>
            <span className="text-[#e4e4ec]">Generate Offers</span> — your
            template is filled from graded, sourced facts
          </li>
          <li>
            Review offers in the{" "}
            <a href="/offers" className="text-[#4a8fe7] hover:underline">
              Offers
            </a>{" "}
            screen before sending
          </li>
        </ol>
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