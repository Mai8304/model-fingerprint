from __future__ import annotations

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.abstention import (
    extract_abstention_v3,
    score_abstention_v3,
)
from modelfingerprint.extractors.boundary_decision import (
    extract_boundary_decision_v1,
    score_boundary_decision_v1,
)
from modelfingerprint.extractors.context_retrieval import (
    extract_context_retrieval_v3,
    score_context_retrieval_v3,
)
from modelfingerprint.extractors.evidence_grounding import (
    extract_evidence_grounding_v3,
    score_evidence_grounding_v3,
)
from modelfingerprint.extractors.mention_classification import (
    extract_mention_classification_v1,
    score_mention_classification_v1,
)
from modelfingerprint.extractors.selection_boundary import (
    extract_selection_boundary_v1,
    score_selection_boundary_v1,
)
from modelfingerprint.extractors.representation_alignment import (
    extract_representation_alignment_v3,
    score_representation_alignment_v3,
)
from modelfingerprint.extractors.state_tracking import (
    extract_state_tracking_v3,
    score_state_tracking_v3,
)


def build_prompt(prompt_id: str, family: str, reference: dict[str, object]) -> PromptDefinition:
    if family == "boundary_decision":
        answer_extractor = "boundary_decision_v1"
        score_extractor = "boundary_decision_score_v1"
    elif family == "mention_classification":
        answer_extractor = "mention_classification_v1"
        score_extractor = "mention_classification_score_v1"
    elif family == "selection_boundary":
        answer_extractor = "selection_boundary_v1"
        score_extractor = "selection_boundary_score_v1"
    else:
        answer_extractor = f"{family}_v3"
        score_extractor = f"{family}_score_v3"
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
                "max_output_tokens": 320,
                "response_format": "text",
                "reasoning_mode": "capture_if_available",
            },
            "output_contract": {"id": "tolerant_json_v3", "canonicalizer": "tolerant_json_v3"},
            "extractors": {
                "answer": answer_extractor,
                "score": score_extractor,
            },
            "evaluation": {"reference": reference},
            "required_capabilities": ["chat_completions"],
            "weight_hint": 1.0,
            "tags": ["v3"],
            "risk_level": "low",
        }
    )


def test_v3_evidence_grounding_scores_current_values_and_abstention() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "owner": "Alice Wong",
                "role": "Primary DBA",
                "region": None,
                "change_window": "2026-03-21 02:00 UTC",
            },
            "evidence": {
                "owner": ["e3"],
                "role": ["e2"],
                "region": [],
                "change_window": ["e5"],
            },
            "unknowns": {"region": "missing"},
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p021",
        "evidence_grounding",
        {
            "expected_task_result": {
                "owner": "Alice Wong",
                "role": "Primary DBA",
                "region": None,
                "change_window": "2026-03-21 02:00 UTC",
            }
        },
    )

    behavior = extract_evidence_grounding_v3(canonical_output)
    scores = score_evidence_grounding_v3(prompt, canonical_output)

    assert behavior["filled_field_count"] == 3
    assert behavior["unknown_field_count"] == 1
    assert scores["value_accuracy"] == 1.0
    assert scores["abstention_compliance"] == 1.0


def test_v3_context_retrieval_scores_order_exclusion_and_paragraphs() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "found_entities": ["alpha", "beta", "gamma", "zephyr"],
                "excluded_entities": ["alpha-2", "zephyr-old", "delta", "gamma-9", "beta-legacy"],
            },
            "evidence": {
                "paragraph_map": {"alpha": "p1", "beta": "p2", "gamma": "p2", "zephyr": "p3"}
            },
            "unknowns": {},
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p022",
        "context_retrieval",
        {
            "expected_task_result": {
                "found_entities": ["alpha", "beta", "gamma", "zephyr"],
                "excluded_entities": ["alpha-2", "zephyr-old", "delta", "gamma-9", "beta-legacy"],
            },
            "expected_evidence": {
                "paragraph_map": {"alpha": "p1", "beta": "p2", "gamma": "p2", "zephyr": "p3"}
            },
        },
    )

    behavior = extract_context_retrieval_v3(canonical_output)
    scores = score_context_retrieval_v3(prompt, canonical_output)

    assert behavior["found_count"] == 4
    assert behavior["excluded_count"] == 5
    assert scores["entity_recall"] == 1.0
    assert scores["paragraph_accuracy"] == 1.0
    assert scores["exclusion_accuracy"] == 1.0


def test_v32_selection_boundary_scores_category_labels() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "m1": "I",
                "m2": "R",
                "m3": "I",
                "m4": "R",
                "m5": "I",
                "m6": "R",
                "m7": "I",
                "m8": "V",
                "m9": "A",
                "m10": "V",
            },
            "evidence": {},
            "unknowns": {},
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p042",
        "selection_boundary",
        {
            "expected_task_result": {
                "m1": "I",
                "m2": "R",
                "m3": "I",
                "m4": "R",
                "m5": "I",
                "m6": "R",
                "m7": "I",
                "m8": "V",
                "m9": "A",
                "m10": "V",
            }
        },
    )

    behavior = extract_selection_boundary_v1(canonical_output)
    scores = score_selection_boundary_v1(prompt, canonical_output)

    assert behavior["include_count"] == 4
    assert behavior["ambiguous_count"] == 1
    assert behavior["variant_count"] == 2
    assert behavior["rejected_count"] == 3
    assert scores["classification_accuracy"] == 1.0
    assert scores["selection_accuracy"] == 1.0
    assert scores["ambiguity_accuracy"] == 1.0
    assert scores["variant_accuracy"] == 1.0
    assert scores["rejection_accuracy"] == 1.0


def test_v3_abstention_scores_answer_unknown_and_conflict_paths() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "q1": {"status": "answer", "value": "yes"},
                "q2": {"status": "unknown", "value": None},
                "q3": {"status": "answer", "value": "retry failed background jobs"},
                "q4": {"status": "conflict_unresolved", "value": None},
                "q5": {"status": "answer", "value": "no"},
                "q6": {"status": "answer", "value": "no"},
            },
            "evidence": {
                "q1": ["e1"],
                "q3": ["e1"],
                "q5": ["e5"],
                "q6": ["e5"],
            },
            "unknowns": {"q2": "missing_actor"},
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p023",
        "abstention",
        {
            "expected_task_result": {
                "q1": {"status": "answer", "value": "yes"},
                "q2": {"status": "unknown", "value": None},
                "q3": {"status": "answer", "value": "retry failed background jobs"},
                "q4": {"status": "conflict_unresolved", "value": None},
                "q5": {"status": "answer", "value": "no"},
                "q6": {"status": "answer", "value": "no"},
            }
        },
    )

    behavior = extract_abstention_v3(canonical_output)
    scores = score_abstention_v3(prompt, canonical_output)

    assert behavior["answered_count"] == 4
    assert behavior["unknown_count"] == 1
    assert behavior["conflict_count"] == 1
    assert behavior["status_q4"] == "conflict_unresolved"
    assert behavior["value_q5"] == "no"
    assert scores["answer_accuracy"] == 1.0
    assert scores["unknown_accuracy"] == 1.0
    assert scores["conflict_accuracy"] == 1.0
    assert scores["match_q5"] is True
    assert scores["match_q6"] is True


def test_v3_state_tracking_scores_snapshot_derivation_and_defaults() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "ticket_a": {"status": "closed", "owner": "ops", "priority": "p1"},
                "ticket_b": {"status": "open", "owner": "db", "priority": "p2"},
                "worker_x": {"status": "suspended", "owner": "ml", "priority": "p3"},
            },
            "evidence": {
                "derivation_codes": {"ticket_a": "r5", "ticket_b": "r6", "worker_x": "r10"},
                "defaults_used": ["ticket_b.priority"],
            },
            "unknowns": {},
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p024",
        "state_tracking",
        {
            "expected_task_result": {
                "ticket_a": {"status": "closed", "owner": "ops", "priority": "p1"},
                "ticket_b": {"status": "open", "owner": "db", "priority": "p2"},
                "worker_x": {"status": "suspended", "owner": "ml", "priority": "p3"},
            },
            "expected_evidence": {
                "derivation_codes": {"ticket_a": "r5", "ticket_b": "r6", "worker_x": "r10"},
                "defaults_used": ["ticket_b.priority"],
            },
        },
    )

    behavior = extract_state_tracking_v3(canonical_output)
    scores = score_state_tracking_v3(prompt, canonical_output)

    assert behavior["resolved_object_count"] == 3
    assert behavior["default_count"] == 1
    assert scores["snapshot_accuracy"] == 1.0
    assert scores["derivation_accuracy"] == 1.0
    assert scores["default_usage_accuracy"] == 1.0


def test_v3_representation_alignment_scores_aliases_ambiguity_and_rejections() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "canonical_entities": ["alice_wong", "db_cluster_east", "zephyr_core"],
                "alias_map": {
                    "Alice W.": "alice_wong",
                    "Alice Wong": "alice_wong",
                    "王艾丽": "alice_wong",
                    "DB-east": "db_cluster_east",
                    "华东数据库集群": "db_cluster_east",
                    "db-cluster-east": "db_cluster_east",
                    "Zephyr Core": "zephyr_core",
                    "zephyr-core": "zephyr_core",
                    "Project Zephyr": "zephyr_core",
                },
                "ambiguous_mentions": ["OW"],
                "rejected_items": ["temp-note"],
            },
            "evidence": {},
            "unknowns": {"OW": "ambiguous"},
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p025",
        "representation_alignment",
        {
            "expected_task_result": {
                "canonical_entities": ["alice_wong", "db_cluster_east", "zephyr_core"],
                "alias_map": {
                    "Alice W.": "alice_wong",
                    "Alice Wong": "alice_wong",
                    "王艾丽": "alice_wong",
                    "DB-east": "db_cluster_east",
                    "华东数据库集群": "db_cluster_east",
                    "db-cluster-east": "db_cluster_east",
                    "Zephyr Core": "zephyr_core",
                    "zephyr-core": "zephyr_core",
                    "Project Zephyr": "zephyr_core",
                },
                "ambiguous_mentions": ["OW"],
                "rejected_items": ["temp-note"],
            }
        },
    )

    behavior = extract_representation_alignment_v3(canonical_output)
    scores = score_representation_alignment_v3(prompt, canonical_output)

    assert behavior["canonical_count"] == 3
    assert behavior["ambiguous_count"] == 1
    assert behavior["rejected_count"] == 1
    assert scores["canonical_accuracy"] == 1.0
    assert scores["rejection_accuracy"] == 1.0


def test_v3_representation_alignment_treats_empty_object_violations_as_empty_list() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "canonical_entities": ["alice_wong"],
                "alias_map": {"Alice W.": "alice_wong"},
                "ambiguous_mentions": [],
                "rejected_items": [],
            },
            "evidence": {},
            "unknowns": {},
            "violations": {},
        },
    )
    prompt = build_prompt(
        "p025",
        "representation_alignment",
        {
            "expected_task_result": {
                "canonical_entities": ["alice_wong"],
                "alias_map": {"Alice W.": "alice_wong"},
                "ambiguous_mentions": [],
                "rejected_items": [],
            }
        },
    )

    behavior = extract_representation_alignment_v3(canonical_output)
    scores = score_representation_alignment_v3(prompt, canonical_output)

    assert behavior["violation_count"] == 0
    assert scores["violation_free"] is True


def test_v3_representation_alignment_accepts_mapping_shaped_entity_collections() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "canonical_entities": {
                    "alice_wong": {"type": "person"},
                    "db_cluster_east": {"type": "resource"},
                },
                "alias_map": {
                    "Alice W.": "alice_wong",
                    "DB-east": "db_cluster_east",
                },
                "ambiguous_mentions": {
                    "OW": ["OpenWhale", "Ops Watch"],
                },
                "rejected_items": {
                    "temp-note": "not an entity",
                },
            },
            "evidence": {},
            "unknowns": {},
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p025",
        "representation_alignment",
        {
            "expected_task_result": {
                "canonical_entities": ["alice_wong", "db_cluster_east"],
                "alias_map": {
                    "Alice W.": "alice_wong",
                    "DB-east": "db_cluster_east",
                },
                "ambiguous_mentions": ["OW"],
                "rejected_items": ["temp-note"],
            }
        },
    )

    behavior = extract_representation_alignment_v3(canonical_output)
    scores = score_representation_alignment_v3(prompt, canonical_output)

    assert behavior["canonical_count"] == 2
    assert behavior["ambiguous_count"] == 1
    assert behavior["rejected_count"] == 1
    assert scores["canonical_accuracy"] == 1.0
    assert scores["ambiguity_preservation"] == 1.0
    assert scores["rejection_accuracy"] == 1.0


def test_boundary_decision_scores_answers_unknowns_and_conflicts() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "q1": {"s": "a", "v": "ops"},
                "q2": {"s": "a", "v": "no"},
                "q3": {"s": "a", "v": "no"},
                "q4": {"s": "a", "v": "override"},
                "q5": {"s": "a", "v": "yes"},
                "q6": {"s": "c", "v": None},
                "q7": {"s": "u", "v": None},
            },
            "evidence": {"q1": ["r1", "r5"], "q4": ["r2"], "q5": ["r5"], "q6": ["r7", "r8"]},
            "unknowns": ["q7"],
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p044",
        "boundary_decision",
        {
            "expected_task_result": {
                "q1": {"s": "a", "v": "ops"},
                "q2": {"s": "a", "v": "no"},
                "q3": {"s": "a", "v": "no"},
                "q4": {"s": "a", "v": "override"},
                "q5": {"s": "a", "v": "yes"},
                "q6": {"s": "c", "v": None},
                "q7": {"s": "u", "v": None},
            }
        },
    )

    behavior = extract_boundary_decision_v1(canonical_output)
    scores = score_boundary_decision_v1(prompt, canonical_output)

    assert behavior["answered_count"] == 5
    assert behavior["unknown_count"] == 1
    assert behavior["conflict_count"] == 1
    assert behavior["status_q1"] == "a"
    assert behavior["value_q1"] == "ops"
    assert behavior["status_q6"] == "c"
    assert "value_q6" not in behavior
    assert scores["decision_accuracy"] == 1.0
    assert scores["boundary_accuracy"] == 1.0
    assert scores["evidence_alignment"] == 1.0
    assert scores["match_q1"] is True
    assert scores["match_q6"] is True


def test_boundary_decision_tolerates_invalid_actual_slots_without_crashing() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "q1": {"status": "answer", "value": "ops"},
                "q2": {"s": "a", "v": "no"},
                "q3": {"s": "a", "v": "no"},
                "q4": {"s": "a", "v": "override"},
                "q5": {"s": "a", "v": "yes"},
                "q6": {"s": "c", "v": None},
                "q7": {"s": "u", "v": None},
            },
            "evidence": {"q1": "r1; r5"},
            "unknowns": ["q7"],
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p044",
        "boundary_decision",
        {
            "expected_task_result": {
                "q1": {"s": "a", "v": "ops"},
                "q2": {"s": "a", "v": "no"},
                "q3": {"s": "a", "v": "no"},
                "q4": {"s": "a", "v": "override"},
                "q5": {"s": "a", "v": "yes"},
                "q6": {"s": "c", "v": None},
                "q7": {"s": "u", "v": None},
            }
        },
    )

    behavior = extract_boundary_decision_v1(canonical_output)
    scores = score_boundary_decision_v1(prompt, canonical_output)

    assert behavior["answered_count"] == 4
    assert behavior["unknown_count"] == 1
    assert behavior["conflict_count"] == 1
    assert scores["decision_accuracy"] < 1.0
    assert scores["boundary_accuracy"] < 1.0


def test_mention_classification_scores_canonical_ambiguous_and_rejected_items() -> None:
    canonical_output = CanonicalizedOutput(
        format_id="tolerant_json_v3",
        payload={
            "task_result": {
                "m1": "C:openwhale_control",
                "m2": "C:openwhale_control",
                "m3": "C:atlas_db_east",
                "m4": "C:atlas_db_east",
                "m5": "M",
                "m6": "M",
                "m7": "M",
                "m8": "R",
                "m9": "R",
                "m10": "R",
                "m11": "R",
                "m12": "R",
            },
            "evidence": {},
            "unknowns": {},
            "violations": [],
        },
    )
    prompt = build_prompt(
        "p045",
        "mention_classification",
        {
            "expected_task_result": {
                "m1": "C:openwhale_control",
                "m2": "C:openwhale_control",
                "m3": "C:atlas_db_east",
                "m4": "C:atlas_db_east",
                "m5": "M",
                "m6": "M",
                "m7": "M",
                "m8": "R",
                "m9": "R",
                "m10": "R",
                "m11": "R",
                "m12": "R",
            }
        },
    )

    behavior = extract_mention_classification_v1(canonical_output)
    scores = score_mention_classification_v1(prompt, canonical_output)

    assert behavior["canonical_count"] == 4
    assert behavior["ambiguous_count"] == 3
    assert behavior["rejected_count"] == 5
    assert scores["classification_accuracy"] == 1.0
    assert scores["ambiguity_accuracy"] == 1.0
    assert scores["rejection_accuracy"] == 1.0
