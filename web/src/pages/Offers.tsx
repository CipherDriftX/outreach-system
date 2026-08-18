import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export default function Offers() {
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

  const handleSave = () => {
    mutation.mutate(text);
  };

  const highlightPlaceholders = (t: string) => {
    return t.replace(
      /(\[[^\]]+\])/g,
      '<span class="text-[#4eca7a]">$1</span>'
    ).replace(
      /(\([^)]+\))/g,
      '<span class="text-[#4a8fe7]">$1</span>'
    );
  };

  if (isLoading) return <div className="text-[#606078] text-sm">Loading…</div>;

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold">Offers</h2>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="text-xs text-[#4eca7a] font-medium">Saved</span>
          )}
          <button
            onClick={handleSave}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-[#4a8fe7] text-white text-xs font-medium rounded-lg hover:bg-[#3a7fd7] transition-colors disabled:opacity-50"
          >
            {mutation.isPending ? "Saving…" : "Save Template"}
          </button>
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-1">
          <textarea
            value={text}
            onChange={(e) => { setText(e.target.value); setSaved(false); }}
            className="w-full h-[400px] bg-transparent text-sm text-[#e4e4ec] font-mono leading-relaxed p-5 resize-none focus:outline-none placeholder-[#606078]"
            placeholder="Write your offer template here… Use [field_name] for facts and (signal_field) for origin signal context."
            spellCheck={false}
          />
        </div>

        <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-5">
          <h3 className="text-xs font-medium text-[#9898b0] uppercase tracking-wider mb-3">
            Preview with highlighting
          </h3>
          <div
            className="text-sm leading-relaxed font-mono whitespace-pre-wrap"
            dangerouslySetInnerHTML={{ __html: highlightPlaceholders(text) }}
          />
        </div>

        <div className="bg-[#0e0e16] border border-[#1e1e2e] rounded-lg p-5">
          <h3 className="text-xs font-medium text-[#9898b0] uppercase tracking-wider mb-3">
            Placeholder reference
          </h3>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <h4 className="text-[#4eca7a] font-medium mb-1">[fact_field] — Lead Facts</h4>
              <ul className="text-[#606078] space-y-0.5">
                <li><code className="text-[#4eca7a]">[company_name]</code> — company name</li>
                <li><code className="text-[#4eca7a]">[contact_first_name]</code> — first name</li>
                <li><code className="text-[#4eca7a]">[pain_summary]</code> — top pain signal</li>
                <li><code className="text-[#4eca7a]">[tech_stack_primary_tools]</code> — tools used</li>
                <li><code className="text-[#4eca7a]">[gap_hypothesis_summary]</code> — one-line need</li>
                <li><code className="text-[#4eca7a]">[gap_hypothesis_explanation]</code> — full explanation</li>
                <li><code className="text-[#4eca7a]">[recent_activity_detail]</code> — latest event</li>
                <li><code className="text-[#4eca7a]">[competitor_name]</code> — competitor</li>
              </ul>
            </div>
            <div>
              <h4 className="text-[#4a8fe7] font-medium mb-1">(signal_field) — Origin Signal</h4>
              <ul className="text-[#606078] space-y-0.5">
                <li><code className="text-[#4a8fe7]">(signal_source_type)</code> — e.g. "job_posting"</li>
                <li><code className="text-[#4a8fe7]">(signal_source_name)</code> — e.g. "reddit"</li>
                <li><code className="text-[#4a8fe7]">(signal_raw_text_snippet)</code> — quote</li>
                <li><code className="text-[#4a8fe7]">(signal_author_handle)</code> — @username</li>
                <li><code className="text-[#4a8fe7]">(signal_url)</code> — link to original</li>
              </ul>
              <h4 className="text-[#f0a050] font-medium mb-1 mt-3">[if fact: value] — Conditionals</h4>
              <ul className="text-[#606078] space-y-0.5">
                <li><code className="text-[#f0a050]">[if tech_stack: any]...[/if]</code></li>
                <li><code className="text-[#f0a050]">[if recent_activity: funding_or_hiring]...[/if]</code></li>
                <li><code className="text-[#f0a050]">[if competitors: switched_from]...[/if]</code></li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}