# Multi-Protocol Transport Architecture Design

**Date**

2026-03-12

**Status**

Approved for planning

**Problem**

The current live execution stack couples three concerns too tightly:

- low-level transport behavior
- provider and protocol compatibility rules
- runtime policy and retry budgeting

That coupling creates avoidable incompatibilities:

- the custom socket-level HTTP client can disagree with a plain direct HTTP baseline
- OpenAI-compatible provider quirks leak into the main adapter instead of staying local
- runtime policy is too coarse and treats "thinking" as a transport strategy instead of a task strategy

The result is a system that is harder to extend, harder to debug, and more likely to regress as more providers and model families are added.

**Goal**

Build a live execution architecture that:

- keeps transport performance and behavior close to the simplest direct HTTP baseline
- supports broad provider coverage without creating one adapter per provider
- treats protocol families as the adapter boundary
- pushes most model and provider differences into endpoint profiles and targeted quirks
- replaces fixed global runtime assumptions with task-aware runtime policy

**Non-Goals**

- no attempt in this phase to support every provider with a first-party adapter immediately
- no one-shot rewrite of all CLI, web API, and artifact contracts at the same time
- no removal of high-budget retries such as `max_tokens=3000`; the change is to make them escalation tiers rather than universal defaults
- no change to prompt-bank semantics, extractor definitions, or comparison scoring in this design phase

**Constraints**

- the architecture should maximize reuse for OpenAI-compatible endpoints
- provider-specific behavior should not force provider-specific adapters unless the wire protocol is genuinely different
- transport and protocol logic must be independently testable
- the migration must be staged so direct live functionality remains shippable after each phase
- timeouts must remain explicit and observable rather than becoming implicit library defaults

## Approaches Considered

1. Minimal migration

Replace the custom HTTP client with `httpx` and leave the rest of the architecture largely intact.

This would improve transport stability quickly, but it would not solve the long-term issue of provider-specific behavior continuing to accumulate inside one adapter and one runtime policy model.

2. Standard long-term architecture

Adopt a single `httpx` transport layer, introduce protocol-family adapters, move provider and model differences into profiles plus targeted quirks, and redesign runtime policy around task intent.

This keeps the migration incremental while establishing a durable architecture boundary for broad compatibility.

3. Full rewrite

Redesign transport, adapters, endpoint schema, runtime policy, and live orchestration in one pass.

This offers the cleanest end state, but it creates the highest migration and verification risk for a codebase that still needs rapid iteration.

**Recommendation**

Use approach 2.

It is the strongest fit for the current repository state:

- transport reliability improves early
- adapter count stays small
- provider quirks stop polluting the standard path
- migration can happen in independently verifiable phases

## Design

### 1. Layered Architecture

The live stack should be split into four explicit layers:

1. `transport`
2. `protocol adapter`
3. `profile + quirk rules`
4. `runtime policy`

Each layer has one job:

- `transport` moves bytes and reports progress, deadlines, and errors
- `protocol adapter` translates between internal prompt/completion models and one wire protocol family
- `profile + quirk rules` express provider and model differences inside a protocol family
- `runtime policy` chooses request budgets and escalation strategy based on task intent and observed results

This boundary keeps transport bugs from masquerading as capability problems and keeps provider quirks from forcing new adapters.

### 2. Adapter Boundary: Protocol Families, Not Providers

Adapters should be defined by wire protocol families rather than by provider brands.

The first target set is:

- `openai_compatible`
- `anthropic_messages`
- `gemini_generate_content`

The rule is:

- if two endpoints accept the same request/response shape with limited variations, they share one adapter
- if the protocol is materially different, create a new adapter

This means most OpenAI-compatible providers should continue to use one adapter even when they require different parameter support, different field mappings, or small request/response workarounds.

### 3. Unified Transport Based on `httpx`

The repository should stop maintaining a socket-level HTTP implementation as the default live path.

The transport layer should be rewritten around `httpx` with:

- a shared client for connection pooling
- explicit per-request timeout configuration
- streaming support for SSE and chunked responses
- normalized transport error mapping
- consistent trace capture for request and response bodies

The transport layer must remain unaware of tools, reasoning, vision, JSON response contracts, or provider names.

It should expose only transport-level concepts:

- blocking JSON response
- event-stream response
- first-byte timing
- progress timing
- total latency
- timeout and network error categories

### 4. Endpoint Profiles Become Protocol Instance Config

`EndpointProfile` should remain the static configuration hub, but its meaning should expand from "field mapping payload" to "protocol instance definition".

Each profile should describe:

- `protocol_family`
- `provider_id`
- `base_url`
- `model`
- capability flags
- request and response mappings
- default transport and retry settings
- quirk identifiers
- runtime profile identifier

Most new models should be onboarded by adding or updating a profile rather than touching adapter code.

### 5. Quirk Rules Absorb Provider And Model Differences

Quirks are the pressure-release valve that prevents a standard adapter from turning into provider-specific code.

Quirks should be small and phase-specific:

- request-time mutation
- response-time normalization
- probe-only retry or fallback logic

Examples include:

- omit unsupported sampling parameters
- disable thinking when a provider rejects forced tool choice
- prefer data URLs during vision probing for providers that reject remote image URLs

The quirk layer must stay narrow:

- quirks should not become alternate adapters
- quirks should not contain business logic
- quirks should be opt-in from endpoint profiles

### 6. Runtime Policy Is Intent-Driven

Runtime policy should stop treating "thinking" as a universal execution class.

Instead, it should key off:

- task intent
- endpoint profile defaults
- capability probe observations
- prior attempt results

The initial task intents should be:

- `structured_extraction`
- `capability_probe`
- `long_reasoning`

Runtime policy should produce attempt tiers rather than a single default budget. For example:

- tier 0: prompt budget or conservative default
- tier 1: escalate on `length`, empty answer, or invalid structured output
- tier 2: high-budget recovery or long-reasoning mode

Under this design, `max_tokens=3000` remains a valid escalation tier, but it is no longer the unconditional default for all models that appear to support thinking.

### 7. Timeout Model

Timeout handling should remain explicit, but the current fixed global interpretation of `10`, `60`, and `120` should be replaced with separate timeout dimensions:

- `connect_timeout_seconds`
- `write_timeout_seconds`
- `first_byte_timeout_seconds`
- `idle_timeout_seconds`
- `total_deadline_seconds`

These values should be set by runtime policy defaults and overrideable by endpoint profiles.

This separates connection failures, no-response failures, stalled-stream failures, and total-budget exhaustion so debugging stays precise.

### 8. Migration Strategy

The migration should happen in phases:

1. replace the transport implementation with `httpx` while preserving existing call sites
2. formalize protocol-family adapters and route endpoint selection through `protocol_family`
3. introduce the quirk registry and move provider-specific exceptions out of adapters
4. redesign runtime policy to generate attempt tiers by task intent
5. add first-class support for non-OpenAI protocol families

Each phase should leave the repository in a shippable state with targeted regression coverage.

### 9. Testing Strategy

Verification should happen at three levels:

1. transport tests
- blocking JSON responses
- SSE parsing
- first-byte, idle, and total timeout behavior
- cancellation and retryable network failures

2. adapter and quirk tests
- request construction
- response parsing
- quirk application order
- provider/model-specific compatibility fixes

3. live smoke tests
- direct HTTP baseline against representative providers
- framework live request against the same endpoint
- latency and payload comparisons for representative OpenAI-compatible, Anthropic, and Gemini-family models

The direct HTTP baseline is important. The framework should be measured against the simplest valid request path rather than only against its own prior behavior.

### 10. Expected Outcome

If implemented correctly, the repository should converge on:

- one standard transport implementation
- a small number of protocol-family adapters
- many endpoint profiles
- a very small number of targeted quirks
- runtime decisions driven by task intent and observed evidence

That is the architecture most likely to improve compatibility breadth and preserve transport efficiency without creating one adapter per provider.
