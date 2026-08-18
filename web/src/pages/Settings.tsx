import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export default function Settings() {
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: api.getSettings,
  });

  if (isLoading) return <div className="text-[#606078] text-sm">Loading…</div>;

  const governors = data?.governors || {};

  return (
    <div className="max-w-3xl">
      <h2 className="text-lg font-semibold mb-6">Settings</h2>

      <div className="space-y-6">
        <Section title="Business">
          <div className="text-sm text-[#9898b0]">
            Business ID: <code className="text-[#e4e4ec] font-mono text-xs">{data?.business_id || "—"}</code>
          </div>
        </Section>

        <Section title="Research Governors">
          {governors.research && typeof governors.research === "object" && (
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(governors.research as Record<string, unknown>).map(([key, value]) => (
                <div key={key} className="flex justify-between items-center py-1.5">
                  <span className="text-xs text-[#9898b0] font-mono">{key}</span>
                  <span className="text-xs text-[#e4e4ec] font-mono">{String(value)}</span>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section title="Craft Governors">
          {governors.craft && typeof governors.craft === "object" && (
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(governors.craft as Record<string, unknown>)
                .filter(([k]) => k !== "default_template")
                .map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center py-1.5">
                    <span className="text-xs text-[#9898b0] font-mono">{key}</span>
                    <span className="text-xs text-[#e4e4ec] font-mono">{String(value)}</span>
                  </div>
                ))}
            </div>
          )}
        </Section>

        <Section title="API Keys">
          <div className="text-xs text-[#606078]">
            Configure API keys in <code className="text-[#9898b0]">.env</code>. Keys are never displayed here.
          </div>
          <div className="mt-2 space-y-1 text-xs text-[#9898b0]">
            <div>OPENROUTER_API_KEY: {process.env.NODE_ENV === "development" ? "•••• (set in .env)" : "hidden"}</div>
            <div>REDDIT_CLIENT_ID: configured via .env</div>
            <div>TWITTER_BEARER_TOKEN: configured via .env</div>
            <div>GITHUB_TOKEN: configured via .env</div>
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-5">
      <h3 className="text-xs font-medium text-[#9898b0] uppercase tracking-wider mb-3">{title}</h3>
      {children}
    </div>
  );
}