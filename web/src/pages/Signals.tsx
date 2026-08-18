import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Signal } from "../lib/types";

const SOURCE_COLORS: Record<string, string> = {
  reddit: "#ff4500",
  twitter: "#1d9bf0",
  hackernews: "#ff6600",
  stackexchange: "#1b84ff",
  upwork: "#14a800",
  github: "#8b949e",
  indeed: "#2164f3",
  bluesky: "#1083fe",
  linkedin: "#0a66c2",
};

export default function Signals() {
  const { data: signals, isLoading } = useQuery({
    queryKey: ["signals"],
    queryFn: () => api.getSignals(100),
  });

  if (isLoading) return <div className="text-[#606078] text-sm">Loading…</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold">Signals</h2>
        <span className="text-xs font-mono text-[#606078]">
          {signals?.length ?? 0} captured
        </span>
      </div>

      {!signals || signals.length === 0 ? (
        <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-8 text-center">
          <p className="text-[#606078] text-sm">No signals captured yet.</p>
          <p className="text-[#606078] text-xs mt-1">Run signal discovery to populate this view.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {signals.map((s) => (
            <SignalRow key={s.id} signal={s} />
          ))}
        </div>
      )}
    </div>
  );
}

function SignalRow({ signal: s }: { signal: Signal }) {
  const color = SOURCE_COLORS[s.source_name] || "#606078";
  return (
    <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-4 hover:border-[#2a2a3a] transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className="inline-block w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: color }}
            />
            <span className="text-xs font-medium text-[#9898b0] uppercase tracking-wider">
              {s.source_name}
            </span>
            <span className="text-xs text-[#606078]">·</span>
            <span className="text-xs text-[#606078]">{s.source_type}</span>
            {s.matched_pattern && (
              <>
                <span className="text-xs text-[#606078]">·</span>
                <span className="text-xs text-[#4a8fe7] font-mono">{s.matched_pattern}</span>
              </>
            )}
          </div>
          <p className="text-sm text-[#e4e4ec] line-clamp-2 leading-relaxed">{s.raw_text}</p>
          <div className="flex items-center gap-3 mt-2">
            {s.url && (
              <a
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#4a8fe7] hover:underline font-mono truncate max-w-[300px]"
              >
                {s.url}
              </a>
            )}
            {s.author_handle && (
              <span className="text-xs text-[#606078] font-mono">@{s.author_handle}</span>
            )}
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          {s.lead_id ? (
            <span className="inline-flex items-center gap-1 text-xs text-[#4eca7a]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4eca7a]" />
              Lead
            </span>
          ) : (
            <span className="text-xs text-[#606078]">No lead</span>
          )}
          <div className="text-xs text-[#606078] mt-1 font-mono">
            {s.posted_at ? new Date(s.posted_at).toLocaleDateString() : "—"}
          </div>
        </div>
      </div>
    </div>
  );
}