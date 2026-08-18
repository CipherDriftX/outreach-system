import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Offer } from "../lib/api";

type Tab = "template" | "generated";

export default function Offers() {
  const [tab, setTab] = useState<Tab>("template");
  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold">Offers</h2>
        <div className="flex gap-1 bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-1">
          <TabButton active={tab === "template"} onClick={() => setTab("template")}>
            Template
          </TabButton>
          <TabButton active={tab === "generated"} onClick={() => setTab("generated")}>
            Generated
          </TabButton>
        </div>
      </div>
      {tab === "template" ? <TemplateEditor /> : <GeneratedOffers />}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-1.5 rounded-md text-xs font-medium transition-colors ${
        active ? "bg-[#1a1a28] text-[#e4e4ec]" : "text-[#606078] hover:text-[#9898b0]"
      }`}
    >
      {children}
    </button>
  );
}

function TemplateEditor() {
  const queryClient = useQueryClient();
  const { data: template, isLoading } = useQuery({
    queryKey: ["offerTemplate"],
    queryFn: api.getTemplate,
  });

  const [text, setText] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (template?.template_text && !text) {
      setText(template.template_text);
    }
  }, [template, text]);

  const mutation = useMutation({
    mutationFn: (t: string) => api.updateTemplate(t),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offerTemplate"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  if (isLoading) return <div className="text-[#606078] text-sm">Loading…</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-xs text-[#606078]">
          Write your offer structure. The system fills{" "}
          <code className="text-[#4eca7a]">[fact_fields]</code> from researched
          facts and <code className="text-[#4a8fe7]">(signal_fields)</code> from
          the origin signal. Saved automatically to the database — persists
          across refresh.
        </p>
        <div className="flex items-center gap-3 flex-shrink-0 ml-4">
          {saved && <span className="text-xs text-[#4eca7a] font-medium">✓ Saved</span>}
          <button
            onClick={() => mutation.mutate(text)}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-[#4a8fe7] text-white text-xs font-medium rounded-lg hover:bg-[#3a7fd7] transition-colors disabled:opacity-50"
          >
            {mutation.isPending ? "Saving…" : "Save Template"}
          </button>
        </div>
      </div>

      <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-1">
        <textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setSaved(false);
          }}
          className="w-full h-[420px] bg-transparent text-sm text-[#e4e4ec] font-mono leading-relaxed p-5 resize-none focus:outline-none placeholder-[#606078]"
          placeholder="Write your offer template here… Use [field_name] for facts and (signal_field) for origin signal context."
          spellCheck={false}
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-5">
          <h3 className="text-xs font-medium text-[#4eca7a] uppercase tracking-wider mb-3">
            [fact_field] — Lead Facts
          </h3>
          <ul className="text-xs text-[#606078] space-y-1.5 font-mono">
            <li><code className="text-[#4eca7a]">[company_name]</code> — company name</li>
            <li><code className="text-[#4eca7a]">[contact_first_name]</code> — first name</li>
            <li><code className="text-[#4eca7a]">[contact_role]</code> — role at company</li>
            <li><code className="text-[#4eca7a]">[pain_summary]</code> — top pain signal</li>
            <li><code className="text-[#4eca7a]">[tech_stack_primary_tools]</code> — tools used</li>
            <li><code className="text-[#4eca7a]">[competitor_name]</code> — competitor/alternative</li>
            <li><code className="text-[#4eca7a]">[recent_activity_detail]</code> — latest event</li>
            <li><code className="text-[#4eca7a]">[gap_hypothesis_summary]</code> — one-line need</li>
            <li><code className="text-[#4eca7a]">[gap_hypothesis_explanation]</code> — full need</li>
            <li><code className="text-[#4eca7a]">[gap_hypothesis_category]</code> — category</li>
          </ul>
        </div>
        <div className="space-y-6">
          <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-5">
            <h3 className="text-xs font-medium text-[#4a8fe7] uppercase tracking-wider mb-3">
              (signal_field) — Origin Signal
            </h3>
            <ul className="text-xs text-[#606078] space-y-1.5 font-mono">
              <li><code className="text-[#4a8fe7]">(signal_source_type)</code> — e.g. forum_post</li>
              <li><code className="text-[#4a8fe7]">(signal_source_name)</code> — e.g. reddit</li>
              <li><code className="text-[#4a8fe7]">(signal_raw_text_snippet)</code> — quote</li>
              <li><code className="text-[#4a8fe7]">(signal_author_handle)</code> — @username</li>
              <li><code className="text-[#4a8fe7]">(signal_url)</code> — link to original</li>
            </ul>
          </div>
          <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-5">
            <h3 className="text-xs font-medium text-[#f0a050] uppercase tracking-wider mb-3">
              [if fact: value] — Conditionals
            </h3>
            <p className="text-xs text-[#606078] leading-relaxed">
              Conditional blocks render only if the referenced fact exists with
              sufficient grade. Missing facts omit the sentence entirely — the
              system never invents.
            </p>
            <ul className="text-xs text-[#606078] space-y-1.5 mt-2 font-mono">
              <li><code className="text-[#f0a050]">[if tech_stack: any]...[/if]</code></li>
              <li><code className="text-[#f0a050]">[if recent_activity: funding_or_hiring]...[/if]</code></li>
              <li><code className="text-[#f0a050]">[if competitors: switched_from]...[/if]</code></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function GeneratedOffers() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: offers, isLoading } = useQuery({
    queryKey: ["offers"],
    queryFn: api.getOffers,
  });

  const { data: selected } = useQuery({
    queryKey: ["offer", selectedId],
    queryFn: () => api.getOffer(selectedId!),
    enabled: !!selectedId,
  });

  const generateMutation = useMutation({
    mutationFn: () => api.generateAllOffers(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offers"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  if (isLoading) return <div className="text-[#606078] text-sm">Loading…</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-xs text-[#606078]">
          Offers generated from your template using each lead's researched facts.
        </p>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="px-3 py-2 bg-[#4a8fe7] text-white text-xs font-medium rounded-lg hover:bg-[#3a7fd7] transition-colors disabled:opacity-50"
        >
          {generateMutation.isPending ? "Building…" : "✧ Generate for researched leads"}
        </button>
      </div>

      {!offers || offers.length === 0 ? (
        <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-8 text-center">
          <p className="text-[#606078] text-sm">
            No offers generated yet. Research leads first, then generate.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-[280px_1fr] gap-6">
          <div className="space-y-2">
            {offers.map((o) => (
              <button
                key={o.id}
                onClick={() => setSelectedId(o.id)}
                className={`w-full text-left bg-[#0e0e16] border rounded-lg p-4 transition-colors ${
                  selectedId === o.id ? "border-[#4a8fe7]" : "border-[#1e1e2e] hover:border-[#2a2a3a]"
                }`}
              >
                <div className="text-sm text-[#e4e4ec] font-medium truncate">
                  {o.company_name || o.contact_name || "Unknown"}
                </div>
                <div className="text-xs text-[#9898b0] truncate mt-1">{o.subject}</div>
                <div className="flex items-center gap-2 mt-2">
                  {o.unresolved_placeholders.length > 0 ? (
                    <span className="text-xs text-[#f0a050]">
                      {o.unresolved_placeholders.length} unresolved
                    </span>
                  ) : (
                    <span className="text-xs text-[#4eca7a]">fully resolved</span>
                  )}
                  <span className="text-xs text-[#606078]">
                    {o.created_at ? new Date(o.created_at).toLocaleDateString() : ""}
                  </span>
                </div>
              </button>
            ))}
          </div>

          <div>
            {selected ? (
              <OfferPreview offer={selected} />
            ) : (
              <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-8 text-center text-[#606078] text-sm">
                Select an offer to preview
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function OfferPreview({ offer }: { offer: Offer }) {
  return (
    <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg overflow-hidden">
      <div className="border-b border-[#1e1e2e] p-5">
        <div className="text-xs text-[#606078] uppercase tracking-wider mb-1">Subject</div>
        <div className="text-sm text-[#e4e4ec] font-medium">{offer.subject}</div>
      </div>
      <div className="p-5">
        <div className="text-xs text-[#606078] uppercase tracking-wider mb-2">Body</div>
        <pre className="text-sm text-[#e4e4ec] font-mono leading-relaxed whitespace-pre-wrap">
          {offer.body}
        </pre>
      </div>
      {offer.unresolved_placeholders.length > 0 && (
        <div className="border-t border-[#1e1e2e] p-4 bg-[#1a1408]">
          <div className="text-xs text-[#f0a050] font-medium mb-1">
            Unresolved placeholders (omitted from output):
          </div>
          <div className="text-xs text-[#9898b0] font-mono">
            {offer.unresolved_placeholders.join(", ")}
          </div>
        </div>
      )}
    </div>
  );
}