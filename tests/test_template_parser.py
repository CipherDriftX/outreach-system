"""Template parser tests — pure, deterministic, no LLM."""

from src.nodes.offer.parser import (
    ConditionalBlock,
    FactToken,
    LiteralToken,
    SignalToken,
    extract_placeholders,
    parse_template,
)


def test_parse_literal_only():
    tokens = parse_template("Hello world")
    assert len(tokens) == 1
    assert isinstance(tokens[0], LiteralToken)
    assert tokens[0].text == "Hello world"


def test_parse_fact_placeholder():
    tokens = parse_template("Hi [contact_first_name],")
    assert len(tokens) == 3
    assert isinstance(tokens[0], LiteralToken)
    assert tokens[0].text == "Hi "
    assert isinstance(tokens[1], FactToken)
    assert tokens[1].key == "contact_first_name"
    assert tokens[1].fact_type == "contact_details"
    assert isinstance(tokens[2], LiteralToken)
    assert tokens[2].text == ","


def test_parse_signal_placeholder():
    tokens = parse_template("from (signal_source_name)")
    assert len(tokens) == 2
    assert isinstance(tokens[0], LiteralToken)
    assert isinstance(tokens[1], SignalToken)
    assert tokens[1].field == "source_name"


def test_parse_conditional_block():
    template = "[if tech_stack: any]Uses [tech_stack_primary_tools].[/if]"
    tokens = parse_template(template)
    assert len(tokens) == 1
    assert isinstance(tokens[0], ConditionalBlock)
    block = tokens[0]
    assert block.condition_fact_type == "tech_stack"
    assert block.condition_value == "any"
    assert any(isinstance(t, FactToken) for t in block.tokens)


def test_parse_nested_conditional():
    template = "[if competitors: switched_from]A [if tech_stack: any]B[/if][/if]"
    tokens = parse_template(template)
    assert len(tokens) == 1
    outer = tokens[0]
    assert isinstance(outer, ConditionalBlock)
    assert any(isinstance(t, ConditionalBlock) for t in outer.tokens)


def test_extract_placeholders():
    template = (
        "Subject: [gap_hypothesis_summary]\n\n"
        "Hi [contact_first_name], from (signal_source_name).\n"
        "[if tech_stack: any]...[/if]"
    )
    result = extract_placeholders(template)
    assert "gap_hypothesis_summary" in result["fact_placeholders"]
    assert "contact_first_name" in result["fact_placeholders"]
    assert "signal_source_name" in result["signal_placeholders"]
    assert "tech_stack:any" in result["conditionals"]


def test_parse_gap_modifiers():
    tokens = parse_template("[gap_hypothesis_summary] [gap_hypothesis_explanation]")
    fact_tokens = [t for t in tokens if isinstance(t, FactToken)]
    assert fact_tokens[0].modifier == "summary"
    assert fact_tokens[1].modifier == "explanation"
    assert fact_tokens[0].fact_type == "gap_hypothesis"