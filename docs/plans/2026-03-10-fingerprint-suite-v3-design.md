# Fingerprint Suite V3 Design

**Problem**

`fingerprint-suite-v2` provides good coverage, but the full 10-prompt suite is too slow for practical black-box testing, especially on thinking-heavy models and slower providers. Simply dropping to 5 prompts by deleting half of v2 would reduce runtime, but it would also remove too much signal because each v2 family currently relies on two complementary prompts.

**Goal**

Create `fingerprint-suite-v3`, a faster 5-prompt suite that preserves the existing minimal capability probes and keeps model-identification quality close to v2 by increasing the information density of each prompt.

**Hard Constraints**

- Capability probes remain unchanged:
  - `tools`
  - `thinking`
  - `streaming`
  - `image`
- Content prompts drop from 10 to 5.
- The 5 prompts must still cover all five content families:
  - evidence grounding
  - context retrieval
  - abstention
  - state tracking
  - representation alignment
- Target end-to-end runtime: about 3 to 5 minutes for the content suite.
- Output protocol should still target JSON objects.
- Canonicalization may repair format, but must never repair semantics.
- V3 must coexist with v2 for side-by-side validation.

**Approaches Considered**

1. Keep v2 and only reduce output-token budgets.
   This lowers cost in some cases, but it does not solve the core issue: the suite still needs 10 content prompts and remains too slow on providers with long reasoning paths.
2. Reuse 5 existing v2 prompts.
   This is the lowest engineering cost, but it would noticeably reduce discrimination because each family would lose the complementary failure mode carried by its second prompt.
3. Build 5 new high-density prompts, one per family.
   This preserves family coverage while recovering lost signal by combining multiple sub-tasks into each prompt.

**Recommendation**

Use option 3.

## Design

### 1. Suite Shape

`fingerprint-suite-v3` should contain exactly five content prompts:

- `p021`: evidence grounding
- `p022`: context retrieval
- `p023`: abstention
- `p024`: state tracking
- `p025`: representation alignment

The capability layer remains external to the suite and unchanged.

### 2. Prompt Construction Principle

Each v3 prompt replaces the information content of two v2 prompts by combining four layers:

1. `core task`
   - objective answerable sub-task with gold outputs
2. `disturbance layer`
   - distractors such as outdated facts, negated entities, near-match strings, or stale versions
3. `restraint layer`
   - one or more intentionally unanswerable or unresolved fields
4. `protocol layer`
   - fixed output schema, forbidden extra text, consistent top-level keys

This lets a single prompt measure:

- correctness
- groundedness
- hallucination resistance
- abstention discipline
- ordering/normalization behavior
- output stability

### 3. Shared JSON Protocol

All five prompts should target the same top-level JSON shape:

```json
{
  "task_result": {},
  "evidence": {},
  "unknowns": {},
  "violations": []
}
```

Field semantics:

- `task_result`
  - the actual answer payload for the prompt
- `evidence`
  - source ids, paragraph ids, or rule ids that justify the answer
- `unknowns`
  - fields that must remain unanswered, with a machine-checkable reason code where appropriate
- `violations`
  - explicit self-reported conflicts or protocol issues; usually empty

The shared top-level protocol reduces format variance across prompts and makes tolerant canonicalization safer.

### 4. Tolerant JSON Principle

V3 should not rely on fully strict JSON parsing alone. Instead it should adopt:

`strict target protocol + tolerant canonicalization + explicit surface penalties`

Tolerant canonicalization is allowed to repair format only:

- remove markdown fences
- remove leading or trailing explanatory text
- extract the first complete JSON object
- normalize approved key aliases
- normalize small shape differences that are explicitly declared by the prompt family

Tolerant canonicalization must not:

- infer missing semantic values
- convert vague prose into guessed structured answers
- fill in missing entities, owners, dates, or states

If semantic guessing would be required, the prompt must remain a `canonicalization_error`.

### 5. Family Designs

#### 5.1 `p021` Evidence Grounding

**Intent**

Combine the v2 grounding behaviors into one prompt:

- current-value extraction
- outdated fact rejection
- evidence binding
- missing-field abstention

**Shape**

- 6 to 8 short evidence lines
- includes current facts, outdated facts, rotation-only facts, and irrelevant background
- one field intentionally missing

**Scored behaviors**

- current value accuracy
- outdated fact rejection
- evidence alignment
- abstention compliance
- violation-free output

#### 5.2 `p022` Context Retrieval

**Intent**

Replace the v2 retrieval pair with one prompt that requires:

- current-validity filtering
- multi-entity retrieval
- first-appearance ordering
- paragraph localization

**Shape**

- 3 to 4 paragraphs
- includes target entities, retired entities, negated entities, and near-match distractors

**Scored behaviors**

- entity precision
- entity recall
- current-validity accuracy
- order accuracy
- paragraph accuracy
- confusion-free retrieval

#### 5.3 `p023` Abstention

**Intent**

Move from simple known-vs-unknown abstention to three-way classification:

- answerable
- unknown
- conflict unresolved

**Shape**

- one shared evidence block
- 5 to 6 sub-questions
- at least:
  - 2 answerable
  - 1 information-insufficient
  - 1 genuinely conflicting

**Scored behaviors**

- answer accuracy
- unknown accuracy
- conflict classification accuracy
- reason-code accuracy
- evidence alignment
- violation-free output

#### 5.4 `p024` State Tracking

**Intent**

Merge both v2 state-tracking prompts into one denser prompt:

- event sequence resolution
- default rule application
- exception rule precedence
- multi-object final snapshot

**Shape**

- 10 to 14 event lines
- 2 to 3 tracked objects
- explicit default and exception rules
- at least one rule override and one default fallback

**Scored behaviors**

- final snapshot accuracy
- default usage accuracy
- exception rule accuracy
- derivation/rule-id accuracy
- violation-free output

#### 5.5 `p025` Representation Alignment

**Intent**

Merge alias alignment and semi-structured normalization into one prompt:

- bilingual alias unification
- old-name/new-name handling
- ambiguous abbreviation preservation
- invalid-row rejection

**Shape**

- mixed Chinese/English references
- includes aliases, old names, abbreviations, and a few invalid or irrelevant rows

**Scored behaviors**

- canonical entity accuracy
- alias-map accuracy
- ambiguity preservation
- invalid-row rejection
- violation-free output

### 6. Scoring Philosophy

V3 should keep the same high-level scoring channels used by v2:

- `score.*`
- `answer.*`
- `reasoning.*`
- `transport.*`
- `surface.*`

But the prompt-level scorers should become denser. Each v3 prompt should expose more than one correctness dimension so that losing half the number of prompts does not halve the information content.

### 7. Surface and Parse Signals

Because v3 uses only five content prompts, each parse failure becomes more costly. V3 should therefore promote parse stability into explicit fingerprint features, including:

- `surface.parse_repaired`
- `surface.repair_event_count`
- `surface.has_extra_prefix_text`
- `surface.has_extra_suffix_text`
- `surface.key_alias_normalized`
- `surface.field_order_match`
- `surface.constraint_retention`

This means a model can still be scored after a safe format repair, but it will not get that repair for free.

### 8. Compatibility Strategy

V3 should coexist with v2 during validation.

Expected validation questions:

- Is v3 materially faster than v2?
- Is v3 more scoreable than a strict-JSON-only 5-prompt suite?
- Does v3 preserve same-model vs cross-model separation?
- Does v3 maintain or improve Top1 identification and margin quality?

V2 remains the reference baseline until v3 demonstrates acceptable discrimination and stability.

## Testing Strategy

Validation for v3 should include:

- prompt-bank schema validation
- canonicalizer unit tests for safe JSON repair rules
- scorer unit tests for all five new prompts
- suite-level compare tests using existing known profiles
- live smoke runs on at least:
  - `glm-5`
  - one non-thinking chat model
  - one second OpenRouter model for cross-model separation

## Decision

Proceed with a new `fingerprint-suite-v3` that introduces five high-density prompts, a tolerant JSON canonicalization path, and a side-by-side validation period against `fingerprint-suite-v2`.
