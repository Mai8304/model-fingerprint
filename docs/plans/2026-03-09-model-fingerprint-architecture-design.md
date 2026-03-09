# Model Fingerprint Architecture Design

Date: 2026-03-09
Status: approved for planning
Scope: independent project; not coupled to OpenWhale runtime, schema, or deployment model

## 1. Context

This project exists to detect whether a proxy API is likely serving the model it claims to serve, or whether it has been "watered down" by routing to another model. The detection target is not network latency, upstream provider identity, or official-vs-unofficial transport. The detection target is the model's own observable behavior.

The chosen method is:

1. run a versioned probe suite against canonical baseline models and build fingerprint files
2. run the same suite, or a screening subset, against a target endpoint
3. extract structured features from responses
4. compare the target vector to the fingerprint library
5. identify the nearest model, then compare that result with the claimed model

The project must remain independent from OpenWhale. It is currently being developed in a separate folder and should continue as a standalone repository with its own lifecycle.

## 2. Goals

1. Build a lightweight, file-based system for model fingerprinting without requiring a database.
2. Support open-set retrieval: find the closest known model first, then evaluate whether the claimed model matches.
3. Preserve extensibility so prompt quality can improve over time without breaking prior suites and fingerprints.
4. Make every verdict reproducible from files on disk: prompts, runs, profiles, calibration, and comparison output.
5. Keep the first implementation pragmatic and auditable: plain files, explicit schemas, small number of extractor families, deterministic comparison rules.

## 3. Non-Goals

1. Prove model identity with legal certainty.
2. Detect transport-layer fraud, provider relays, or official account ownership.
3. Depend on prompt injection, hidden system prompts, or watermark-style techniques.
4. Optimize for a fully dynamic adaptive query strategy in v1.
5. Introduce a heavy data platform, database, or distributed service.

## 4. Design Principles

1. Structured features over raw-text matching.
2. Versioned suites over ad hoc prompt collections.
3. File artifacts over hidden state.
4. Robust statistics over fragile exact-match rules.
5. Screening first, full-suite confirmation second.
6. Clear separation between protocol source files and generated artifacts.

## 5. High-Level Architecture

The system is composed of six layers:

1. Prompt bank
   - Stores candidate prompts and released suites.
   - Candidate pool is the research space.
   - Released suites are the stable, versioned protocols.

2. Extractor layer
   - Converts raw model outputs into structured features.
   - A prompt references one extractor family and version.

3. Run pipeline
   - Executes a suite against a target endpoint.
   - Captures raw output, usage metadata, and extracted features.
   - Writes an immutable run artifact to disk.

4. Profile builder
   - Aggregates repeated baseline runs into a canonical fingerprint file.
   - Stores robust per-feature summaries such as median and MAD.

5. Calibration and comparison
   - Computes similarity between a target run and each fingerprint.
   - Calibrates verdict thresholds using baseline runs.
   - Emits Top1, Top2, margin, claimed-model similarity, and verdict.

6. CLI and reporting
   - Validates prompt bank files.
   - Executes suites.
   - Builds profiles.
   - Calibrates thresholds.
   - Compares runs to the fingerprint library.

## 6. Repository Layout

Recommended repository layout:

```text
modelfingerprint/
  docs/
    plans/
    tasks/
  prompt-bank/
    candidates/
      p001.yaml
      p002.yaml
      ...
    suites/
      fingerprint-suite-v1.yaml
      quick-check-v1.yaml
  extractors/
    style_brief_v1.yaml
    strict_format_v1.yaml
    minimal_diff_v1.yaml
    structured_extraction_v1.yaml
    retrieval_v1.yaml
  profiles/
    fingerprint-suite-v1/
      claude-ops-4.6.json
      gpt-5.3.json
  calibration/
    fingerprint-suite-v1.json
  runs/
    2026-03-09/
      suspect-a.fingerprint-suite-v1.json
  schemas/
    prompt.schema.json
    run.schema.json
    profile.schema.json
    calibration.schema.json
  src/
    modelfingerprint/
      ...
  tests/
    ...
```

Source code and generated artifacts must remain separate.

## 7. Protocol Layering

The protocol is deliberately split into three tiers.

### 7.1 Research Set: `research-set-v1`

Purpose:
- research space for prompt design
- offline evaluation of discrimination quality
- source pool for future released suites

Size target:
- 40 to 50 prompts

Properties:
- broad coverage
- redundancy allowed
- not used directly for production verdicts

### 7.2 Standard Suite: `fingerprint-suite-v1`

Purpose:
- canonical suite for profile generation
- full comparison suite for dispute resolution
- stable release artifact

Size target:
- about 20 prompts

Properties:
- selected from the research set
- frozen once released
- every prompt must be discriminative, stable, and automatically extractable

### 7.3 Quick-Check Suite: `quick-check-v1`

Purpose:
- low-cost initial screening
- produce Top1/Top2 candidates quickly
- decide whether to stop or escalate to the full suite

Size target:
- 10 to 12 prompts

Properties:
- must be a strict subset of `fingerprint-suite-v1`
- cannot drift into an unrelated protocol
- optimized for cost and discriminative efficiency

Relationship:

```text
research-set-v1 -> fingerprint-suite-v1 -> quick-check-v1
      50                20             10-12
```

## 8. Prompt Families

The first release should use five prompt families only. New prompts should prefer an existing family before inventing a new one.

### 8.1 `style_brief`

Measures short-form style and decision framing.

Typical prompt constraints:
- hard cap on words, characters, or sentences
- compact trade-off explanation
- no long essay output

Representative features:
- `char_len`
- `sentence_count`
- `opens_with_conclusion`
- `uses_numbered_list`
- `hedge_density`
- `directness_score`
- `abstraction_level`
- `example_usage_rate`

### 8.2 `strict_format`

Measures format obedience and local generation habits.

Typical prompt constraints:
- output JSON or fixed tags only
- fixed field order
- no extra text allowed

Representative features:
- `valid_format`
- `has_extra_text`
- `field_order_match`
- `enum_choice_pattern`
- `repair_tendency`
- `constraint_retention`

### 8.3 `minimal_diff`

Measures code-edit style and minimality.

Typical prompt constraints:
- output unified diff only
- strict change-line budget
- no refactor, no reordering, no extra cleanup

Representative features:
- `changed_lines`
- `touched_hunks`
- `refactor_tendency`
- `reorder_tendency`
- `comment_insertion_rate`
- `minimality_score`

### 8.4 `structured_extraction`

Measures grounded extraction and hallucination resistance.

Typical prompt constraints:
- extract fields from supplied text only
- require evidence ids
- forbid outside knowledge

Representative features:
- `field_accuracy`
- `evidence_alignment`
- `hallucinated_fields`
- `normalization_style`
- `missing_field_pattern`

### 8.5 `retrieval`

Measures long-context lookup behavior and error pattern.

Typical prompt constraints:
- multi-needle retrieval from a long text
- fixed JSON output
- similar distractors included

Representative features:
- `needle_hit_count`
- `wrong_needle_type`
- `order_preservation`
- `confusion_pattern`
- `position_sensitivity`

## 9. Research Set Composition

Recommended first-pass composition for a 50-prompt research set:

- `style_brief`: 12
- `strict_format`: 10
- `minimal_diff`: 8
- `structured_extraction`: 10
- `retrieval`: 10

Recommended released composition for `fingerprint-suite-v1`:

- `style_brief`: 5
- `strict_format`: 4
- `minimal_diff`: 3
- `structured_extraction`: 4
- `retrieval`: 4

Recommended released composition for `quick-check-v1`:

- `style_brief`: 3
- `strict_format`: 3
- `minimal_diff`: 2
- `structured_extraction`: 2
- `retrieval`: 2

## 10. Prompt Selection Rules

Candidate prompts are not selected because they are clever. They are selected because they reliably separate models.

Each prompt is scored on four dimensions:

1. discrimination
2. stability
3. extractability
4. cost

Recommended weighted score:

```text
score = 0.40 * discrimination
      + 0.30 * stability
      + 0.20 * extractability
      + 0.10 * cost
```

Hard rejection rules:

1. unstable on repeated baseline runs
2. cannot be automatically feature-extracted
3. materially duplicates an already selected prompt

Selection method:

1. evaluate all candidate prompts offline against multiple canonical models
2. rank prompts within each family
3. apply family quotas when building `fingerprint-suite-v1`
4. choose the lowest-cost, high-discrimination subset for `quick-check-v1`

## 11. Artifact Models

### 11.1 Prompt Definition

Each prompt file should contain:

- `id`
- `name`
- `family`
- `intent`
- `template`
- `variables`
- `output_contract`
- `extractor`
- `weight_hint`
- `tags`
- `risk_level`

Example:

```yaml
id: p017
name: concise_architecture_tradeoff
family: style_brief
intent: distinguish compact trade-off framing
template: |
  用不超过120字说明为什么事件溯源不适合作为所有系统的默认架构。
output_contract:
  type: plain_text
extractor: style_brief_v1
weight_hint: 0.8
tags: [style, architecture, concise]
risk_level: low
```

### 11.2 Run Artifact

A run artifact captures one suite execution for one target.

Required fields:
- run id
- suite id
- target label
- claimed model, if known
- per-prompt raw output
- per-prompt usage metadata
- per-prompt extracted features

### 11.3 Profile Artifact

A profile artifact captures the canonical fingerprint of one model under one suite.

Required fields:
- model id
- suite id
- sample count
- per-prompt feature summaries
- per-prompt weight

The first release should use robust summaries:
- numeric features: median and MAD
- boolean features: empirical `p_true`
- enum features: smoothed empirical distribution

### 11.4 Calibration Artifact

A calibration artifact stores suite-specific thresholds and distributions.

Required fields:
- suite id
- match threshold
- suspicious threshold
- unknown threshold
- margin threshold
- consistency threshold
- summary stats from same-model and cross-model comparisons

## 12. Similarity Model

The selected approach is structured feature vector similarity.

Comparison happens at three levels:

1. feature similarity
2. prompt similarity
3. model similarity

### 12.1 Feature Similarity

Numeric features:
- compare target value to canonical median
- normalize distance by MAD
- convert to bounded similarity score

Boolean features:
- compare observed value to canonical `p_true`
- use simple smoothed probability-based score

Enum features:
- compare observed class to canonical empirical distribution

### 12.2 Prompt Similarity

For each prompt:

```text
prompt_similarity = weighted average of feature similarities
```

### 12.3 Overall Similarity

For a target run and one model profile:

```text
overall_similarity = weighted average of prompt similarities
```

Recommended default feature-group weights:

- format: 0.30
- style: 0.30
- behavior: 0.30
- token usage: 0.10

Token usage is optional and auxiliary. It must never dominate the verdict.

## 13. Retrieval Mode and Verdicts

The system operates in open-set retrieval mode.

For each target:

1. compare against every known profile
2. rank models by similarity
3. take Top1 and Top2
4. compare Top1 with the claimed model
5. produce a verdict

Required comparison output:

- `top1_model`
- `top1_similarity`
- `top2_model`
- `top2_similarity`
- `margin`
- `claimed_model`
- `claimed_model_similarity`
- `consistency`
- `verdict`

Recommended verdict classes:

- `match`
- `suspicious`
- `mismatch`
- `unknown`

Recommended meanings:

- `match`: Top1 is the claimed model, similarity is high, margin is healthy, consistency is high
- `suspicious`: claimed model is plausible but evidence is weak or too close to another model
- `mismatch`: Top1 is not the claimed model and the distance is meaningful
- `unknown`: target is not close to any known profile

## 14. Consistency

Consistency is required in addition to aggregate similarity.

Recommended definition:
- the fraction of prompts whose per-prompt nearest model agrees with the overall Top1 model

Why it matters:
- detects unstable targets
- surfaces mixed behavior
- prevents a small number of prompts from dominating a misleading global score

## 15. Versioning and Evolution

Rules:

1. research set may grow over time
2. released suites are immutable once published
3. `screening-vN` must remain a subset of `default-vN`
4. material prompt changes require a new prompt id or a new suite version
5. material extractor changes require a new extractor version and profile rebuild
6. scores from different suite versions must not be compared directly

Triggers for `default-v2`:

1. new prompts materially improve separation
2. recurring ambiguity between close models
3. an extractor family proves insufficient
4. the known model library expands enough to invalidate previous coverage

## 16. Recommended Tech Stack

Recommended first implementation:

- Python 3.12+
- Typer for CLI
- Pydantic v2 for typed contracts
- PyYAML for prompt and suite files
- `jsonschema` for artifact schema validation
- pytest for tests
- Ruff and mypy for quality gates

Rationale:
- fast iteration
- strong file and JSON handling
- low ceremony
- suitable for data-oriented CLI tooling

## 17. Testing Strategy

Test layers:

1. unit tests
   - prompt validation
   - extractor behavior
   - profile aggregation
   - comparator math
   - verdict rules

2. contract tests
   - sample YAML prompt files validate against schema
   - run/profile/calibration JSON validates against schema

3. fixture tests
   - known raw outputs produce expected extracted features

4. integration tests
   - screening suite execution writes a valid run file
   - profile build from fixture runs produces the expected profile
   - comparison against sample profiles yields the expected Top1 and verdict

5. smoke tests
   - CLI commands are wired and return predictable output

## 18. Delivery Phases

Recommended delivery order:

1. repository foundation and typed contracts
2. prompt-bank schemas and extractor families
3. run pipeline and profile builder
4. calibration and comparison engine
5. CLI commands, reporting, and end-to-end fixtures
6. prompt-bank expansion and suite curation for v1 release

## 19. Acceptance Criteria

The project is ready for first meaningful use when all of the following are true:

1. candidate prompts and released suites validate from disk
2. each extractor family has fixture-backed tests
3. a suite run produces a valid run artifact
4. repeated baseline runs can be aggregated into a valid profile artifact
5. calibration produces suite-specific thresholds
6. comparison returns Top1, Top2, margin, claimed-model similarity, consistency, and verdict
7. the same run can be replayed from files and reproduce the same verdict

## 20. Operational Notes

1. The repository should be initialized as its own git project before implementation starts.
2. Profile files and calibration files are build artifacts, but they should remain human-readable JSON.
3. Canonical profiles should be regenerated whenever a released suite or extractor version changes.
4. The system should avoid hidden mutable state; if an outcome matters, it should be represented on disk.
