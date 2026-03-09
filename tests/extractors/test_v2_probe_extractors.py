from __future__ import annotations

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.abstention import (
    extract_abstention,
    score_abstention,
)
from modelfingerprint.extractors.context_retrieval import (
    extract_context_retrieval,
    score_context_retrieval,
)
from modelfingerprint.extractors.evidence_grounding import (
    extract_evidence_grounding,
    score_evidence_grounding,
)
from modelfingerprint.extractors.representation_alignment import (
    extract_representation_alignment,
    score_representation_alignment,
)
from modelfingerprint.extractors.state_tracking import (
    extract_state_tracking,
    score_state_tracking,
)


def build_prompt(prompt_id: str, family: str, reference: dict[str, object]) -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": prompt_id,
            "name": prompt_id,
            "family": family,
            "intent": prompt_id,
            "messages": [{"role": "user", "content": "Return JSON only."}],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 256,
                "response_format": "text",
                "reasoning_mode": "capture_if_available",
            },
            "output_contract": {"id": "strict_json_v2", "canonicalizer": "strict_json_v2"},
            "extractors": {
                "answer": f"{family}_v1",
                "score": f"{family}_score_v1",
            },
            "evaluation": {"reference": reference},
            "required_capabilities": ["chat_completions"],
            "weight_hint": 1.0,
            "tags": ["v2"],
            "risk_level": "low",
        }
    )


def test_evidence_grounding_extracts_behavior_and_correctness() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="strict_json_v2",
        payload={
            "task_result": {"owner": "Alice Wong", "role": "Primary DBA", "region": None},
            "evidence": {"owner": ["e1"], "role": ["e2"], "region": []},
            "unknown_fields": ["region"],
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p011",
        "evidence_grounding",
        {
            "expected_task_result": {
                "owner": "Alice Wong",
                "role": "Primary DBA",
                "region": None,
            }
        },
    )

    behavior = extract_evidence_grounding(canonical_output)
    scores = score_evidence_grounding(prompt, canonical_output)

    assert behavior["filled_field_count"] == 2
    assert behavior["unknown_field_count"] == 1
    assert scores["value_accuracy"] == 1.0
    assert scores["abstention_compliance"] == 1.0


def test_v2_extractors_tolerate_null_or_scalar_list_fields() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="strict_json_v2",
        payload={
            "task_result": {
                "current_lead": "Priya",
                "backup_lead": None,
                "change_window": "2026-03-21 02:00 UTC",
            },
            "evidence": {
                "current_lead": "[e1]",
                "backup_lead": "[e2]",
                "change_window": "[e3]",
            },
            "unknown_fields": None,
            "violations": None,
        },
    )
    prompt = build_prompt(
        "p012",
        "evidence_grounding",
        {
            "expected_task_result": {
                "current_lead": "Priya",
                "backup_lead": None,
                "change_window": "2026-03-21 02:00 UTC",
            }
        },
    )

    scores = score_evidence_grounding(prompt, canonical_output)

    assert scores["value_accuracy"] == 1.0
    assert scores["violation_free"] is True


def test_context_retrieval_scores_hits_order_and_paragraphs() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="strict_json_v2",
        payload={
            "found_entities": ["alpha", "beta", "gamma"],
            "paragraph_map": {"alpha": "p1", "beta": "p2", "gamma": "p3"},
            "excluded_entities": ["alpha-2"],
            "confusions": [],
        },
    )
    prompt = build_prompt(
        "p013",
        "context_retrieval",
        {
            "expected_found_entities": ["alpha", "beta", "gamma"],
            "expected_paragraph_map": {"alpha": "p1", "beta": "p2", "gamma": "p3"},
        },
    )

    behavior = extract_context_retrieval(canonical_output)
    scores = score_context_retrieval(prompt, canonical_output)

    assert behavior["found_count"] == 3
    assert behavior["confusion_count"] == 0
    assert scores["entity_recall"] == 1.0
    assert scores["paragraph_accuracy"] == 1.0


def test_abstention_scores_unknown_handling() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="strict_json_v2",
        payload={
            "answers": {"q1": "approved", "q2": None, "q3": "retry"},
            "unknowns": ["q2"],
            "evidence": {"q1": ["e1"], "q2": [], "q3": ["e3"]},
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p015",
        "abstention",
        {
            "expected_answers": {"q1": "approved", "q2": None, "q3": "retry"},
        },
    )

    behavior = extract_abstention(canonical_output)
    scores = score_abstention(prompt, canonical_output)

    assert behavior["answered_count"] == 2
    assert behavior["unknown_count"] == 1
    assert scores["answer_accuracy"] == 1.0
    assert scores["abstention_accuracy"] == 1.0


def test_state_tracking_scores_final_snapshot_and_derivations() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="strict_json_v2",
        payload={
            "task_result": {
                "ticket_a": {"status": "closed", "owner": "ops", "priority": "p1"},
                "ticket_b": {"status": "open", "owner": "db", "priority": "p2"},
            },
            "derivation_codes": {"ticket_a": "r3", "ticket_b": "r1"},
            "defaults_used": ["ticket_b.priority"],
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p017",
        "state_tracking",
        {
            "expected_task_result": {
                "ticket_a": {"status": "closed", "owner": "ops", "priority": "p1"},
                "ticket_b": {"status": "open", "owner": "db", "priority": "p2"},
            },
            "expected_derivation_codes": {"ticket_a": "r3", "ticket_b": "r1"},
            "expected_defaults_used": ["ticket_b.priority"],
        },
    )

    behavior = extract_state_tracking(canonical_output)
    scores = score_state_tracking(prompt, canonical_output)

    assert behavior["resolved_object_count"] == 2
    assert behavior["default_count"] == 1
    assert scores["snapshot_accuracy"] == 1.0
    assert scores["derivation_accuracy"] == 1.0


def test_state_tracking_score_degrades_instead_of_crashing_on_weak_shapes() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="strict_json_v2",
        payload={
            "task_result": {
                "ticket_a": {"status": "closed", "owner": "ops", "priority": "p1"},
            },
            "derivation_codes": ["r4 retained owner"],
            "defaults_used": ["ticket_a priority default p2 overridden"],
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p017",
        "state_tracking",
        {
            "expected_task_result": {
                "ticket_a": {"status": "closed", "owner": "ops", "priority": "p1"},
            },
            "expected_derivation_codes": {"ticket_a": "r4"},
            "expected_defaults_used": ["ticket_a.priority"],
        },
    )

    scores = score_state_tracking(prompt, canonical_output)

    assert scores["snapshot_accuracy"] == 1.0
    assert scores["derivation_accuracy"] == 0.0


def test_state_tracking_tolerates_mapping_defaults_used_shape() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="strict_json_v2",
        payload={
            "task_result": {
                "worker_x": {"status": "suspended", "owner": "ml", "priority": "p3"},
                "worker_y": {"status": None, "owner": "ops", "priority": "p1"},
            },
            "derivation_codes": {
                "worker_x": ["r1", "r4"],
                "worker_y": ["r2", "r3", "r5"],
            },
            "defaults_used": {
                "worker_x": {"priority": "p3"},
                "worker_y": {"priority": "p3"},
            },
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p018",
        "state_tracking",
        {
            "expected_task_result": {
                "worker_x": {"status": "suspended", "owner": "ml", "priority": "p3"},
                "worker_y": {"status": "open", "owner": "ops", "priority": "p1"},
            },
            "expected_derivation_codes": {"worker_x": "r4", "worker_y": "r5"},
            "expected_defaults_used": ["worker_x.priority"],
        },
    )

    behavior = extract_state_tracking(canonical_output)
    scores = score_state_tracking(prompt, canonical_output)

    assert behavior["default_count"] == 2
    assert scores["default_usage_accuracy"] == 1.0


def test_representation_alignment_scores_aliases_and_ambiguity() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="strict_json_v2",
        payload={
            "canonical_entities": ["alice_wong", "db_cluster_east"],
            "alias_map": {
                "Alice W.": "alice_wong",
                "DB-east": "db_cluster_east",
            },
            "ambiguous_mentions": ["OW"],
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p019",
        "representation_alignment",
        {
            "expected_canonical_entities": ["alice_wong", "db_cluster_east"],
            "expected_alias_map": {
                "Alice W.": "alice_wong",
                "DB-east": "db_cluster_east",
            },
            "expected_ambiguous_mentions": ["OW"],
        },
    )

    behavior = extract_representation_alignment(canonical_output)
    scores = score_representation_alignment(prompt, canonical_output)

    assert behavior["canonical_count"] == 2
    assert behavior["alias_count"] == 2
    assert scores["canonical_accuracy"] == 1.0
    assert scores["ambiguity_preservation"] == 1.0
