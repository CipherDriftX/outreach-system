"""Offer builder tests — deterministic resolution, no LLM."""

from src.nodes.offer.builder import build_offer


def _fixture() -> tuple[dict, dict, list[dict]]:
    lead = {"company_name": "Acme Corp", "contact_name": "Jane Doe", "contact_email": "jane@acme.com"}
    signal = {
        "source_type": "forum_post",
        "source_name": "reddit",
        "url": "https://reddit.com/r/example/post1",
        "author_handle": "jdoe",
        "raw_text": "We're drowning in manual invoice processing and looking for automation options.",
    }
    facts = [
        {
            "id": "f1",
            "fact_type": "gap_hypothesis",
            "fact": "Acme needs automated invoice processing because their AP team is overloaded, evidenced by their post seeking automation options.",
            "grade": "strong",
            "corroboration_count": 3,
            "source_url": "https://reddit.com/r/example/post1",
        },
        {
            "id": "f2",
            "fact_type": "contact_details",
            "fact": "Jane Doe",
            "grade": "strong",
            "corroboration_count": 2,
        },
        {
            "id": "f3",
            "fact_type": "tech_stack",
            "fact": "QuickBooks, Excel, manual entry",
            "grade": "moderate",
            "corroboration_count": 2,
        },
        {
            "id": "f4",
            "fact_type": "pain_signals",
            "fact": "AP team processes 500 invoices monthly by hand",
            "grade": "strong",
            "corroboration_count": 3,
        },
    ]
    return lead, signal, facts


def test_build_offer_resolves_facts():
    lead, signal, facts = _fixture()
    template = (
        "Subject: [gap_hypothesis_summary] — quick question\n\n"
        "Hi [contact_first_name],\n\n"
        "I saw your (signal_source_name) post about (signal_raw_text_snippet).\n"
        "[if tech_stack: any]\nI noticed you use [tech_stack_primary_tools].\n[/if]"
    )
    result = build_offer(template, lead, signal, facts)
    assert result["subject"].startswith("Acme needs automated invoice processing")
    assert "Jane Doe" in result["body"]
    assert "reddit" in result["body"]
    assert "I noticed you use" in result["body"]
    assert "QuickBooks" in result["body"]
    assert "f2" in result["resolved_fact_ids"]
    assert "f1" in result["resolved_fact_ids"]
    assert result["fully_resolved"]


def test_missing_fact_omits_conditional_block():
    lead, signal, facts = _fixture()
    template = "Start\n[if competitors: switched_from]\nWe help teams switch.\n[/if]\nEnd"
    result = build_offer(template, lead, signal, facts)
    assert "We help teams switch" not in result["body"]
    assert "Start" in result["body"]
    assert "End" in result["body"]


def test_unresolved_fact_omits_line():
    lead, signal, facts = _fixture()
    # recent_activity has no facts in the fixture → unresolved
    template = "Hi [recent_activity_detail],\n\nNext line."
    result = build_offer(template, lead, signal, facts)
    assert "[UNRESOLVED" not in result["body"]
    assert "recent_activity_detail" in result["unresolved_placeholders"]
    assert "Hi" not in result["body"]  # the whole line is dropped
    assert "Next line." in result["body"]


def test_weak_grade_blocks_fact():
    lead, signal, facts = _fixture()
    facts.append(
        {
            "id": "f5",
            "fact_type": "competitors",
            "fact": "Switched from ManualEntry Pro",
            "grade": "weak",
            "corroboration_count": 1,
        }
    )
    template = "[if competitors: switched_from]switched[/if]"
    result = build_offer(template, lead, signal, facts, grade_floor="moderate")
    assert "switched" not in result["body"]


def test_signal_snippet_truncated():
    lead, signal, facts = _fixture()
    template = "(signal_raw_text_snippet)"
    result = build_offer(template, lead, signal, facts)
    snippet = result["body"]
    assert len(snippet) <= 161
    assert snippet.startswith("We're drowning")