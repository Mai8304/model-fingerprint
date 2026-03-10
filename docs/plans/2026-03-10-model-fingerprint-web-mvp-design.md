# Model Fingerprint Web MVP Design

**Date**

2026-03-10

**Status**

Approved for planning

**Problem**

The repository currently provides a file-based model-fingerprint engine and CLI, but it does not provide a user-facing web surface for interactive live checks. The target MVP is not a marketing homepage. It is a single-page online detection console for developers and technical researchers who want to verify whether a model endpoint behaves like the model it claims to be.

The page must support a real backend run, not a static demo:

- users enter `API Key`, `Base URL`, and `Model Name`
- users choose one prebuilt fingerprint model to compare against
- the system runs five high-information prompts
- the page shows progress and prompt-level status during a run that may take about ten minutes
- the page explains both successful conclusions and partial/error outcomes without overstating certainty

**Goal**

Design a single-page, research-tool-style web interface built with official `shadcn/ui` components and official icon usage that:

- starts a real live fingerprint check
- makes the ten-minute runtime feel observable and trustworthy
- clearly separates final conclusions from partial evidence
- supports English, Simplified Chinese, and Japanese
- supports `light`, `dark`, and `system` themes

**Hard Constraints**

- The MVP is a single-page online detection console, not a homepage.
- No login or registration flow.
- The page targets developers and technical researchers first.
- Visual direction: research-lab style, not a generic SaaS landing page and not a heavy terminal dashboard.
- Users provide:
  - `API Key`
  - `Base URL`
  - `Model Name`
  - a selected prebuilt fingerprint model
- The check uses exactly five prompts.
- Typical end-to-end runtime is about ten minutes.
- Progress must show:
  - overall run progress
  - currently active prompt
  - status of all five prompts
- Results must support:
  - one-sentence conclusion
  - similarity / match expression
  - confidence interval
  - fallback "more similar model" when the selected fingerprint is not the closest match
- If the endpoint cannot provide enough usable data, the page must explain the failure state using the upstream status/error information.
- `API Key` is used for the current check only and must not be presented as persisted state.
- UI implementation must use official `shadcn/ui` components and official `lucide-react` icon usage.
- Internationalization rules:
  - default to English
  - if the system language maps to `zh-CN`, use Simplified Chinese
  - if the system language maps to `ja`, use Japanese
  - allow manual language switching
- Theme rules:
  - support `Light`
  - support `Dark`
  - support `System`
- Theme or language changes must not reset an in-flight run.

**Approaches Considered**

1. Homepage-first product page with a detection section below the fold.
   This is stronger for public marketing, but it weakens the MVP's main value: interactive checking.
2. Single-page, three-section vertical tool page.
   This is simple and safe, but it makes long-running progress and result comparison feel cramped.
3. Two-column interactive lab console.
   This keeps model configuration fixed on the left and makes the right side a live workspace for progress, errors, and results.

**Recommendation**

Use option 3.

## Design

### 1. Page Shape

The page should behave like an online experiment console.

Desktop layout:

- top utility bar
- left column: fixed-width configuration panel
- right column: adaptive workbench panel

Mobile layout:

- same sections
- stacked vertically
- configuration first, workbench second

Recommended desktop proportions:

- max width: about `1280px`
- left column: `380px`
- right column: flexible, minimum `640px`
- gap between columns: `16px`

### 2. Top Utility Bar

The top bar should stay compact. It is not a hero section.

Required elements:

- product title: `Model Fingerprint`
- one-line subtitle
- language switcher
- theme switcher
- method/help entry point

Representative subtitle:

- English:
  - `Identify whether a model is what it claims to be through fingerprint comparison.`
- Simplified Chinese:
  - `通过模型指纹比对，判断一个模型是否与其声明身份一致。`
- Japanese:
  - `モデル指紋比較により、対象モデルが申告どおりのモデルかを判定します。`

### 3. Left Column: Configuration Panel

The left column is the operator control panel.

Required fields:

- `API Key`
- `Base URL`
- `Model Name`
- `Fingerprint Model` selector

Required actions:

- `Start Check`
- `Stop Check` during execution
- `Run Again` after completion

Required persistent note:

- security note that the API key is used only for the current run and is not persisted as user-visible state

Suggested supporting copy:

- English:
  - `Your API key is used only for this check and is not stored after the request completes.`

Also place a compact, collapsible `How it works` block in this column or at the lower edge of the workbench, not as a large page section.

### 4. Right Column: Workbench

The right column is the live execution surface.

It should contain the following blocks in stable top-down order:

1. global status card
2. current-prompt card
3. five-prompt status table/list
4. result/conclusion card
5. collapsible run log

This order must stay consistent across states so the user never has to relearn the page during a ten-minute run.

### 5. Empty State

Before the run starts, the workbench should not look blank.

It should show:

- a short explanation of what the run does
- expected run duration
- five-prompt structure
- a compact method summary

Representative content:

- the system sends five high-information probe prompts
- the system extracts response features such as instruction following, information density, capability behavior, and expression style
- the system compares those features with a prebuilt fingerprint model and returns a confidence-bearing conclusion

### 6. Running State

The running experience must answer three user questions continuously:

1. is the system still alive
2. which prompt is currently running
3. if something failed, is the run still continuing

The global status card should show:

- run title: `Running model fingerprint check`
- completed prompt count
- failed prompt count if any
- pending prompt count if any
- estimated remaining time
- overall progress bar

The current-prompt card should show:

- current prompt index, for example `Prompt 3 / 5`
- human-readable probe name
- short description
- current state message such as waiting for response or extracting features
- elapsed time

The five-prompt status area should show one row/card per prompt with:

- probe name
- state
- elapsed time
- short summary or short failure label

The log area should be collapsed by default and expose only high-value events.

### 7. Prompt Naming

The five prompt names should look like research probes, not internal ids.

Recommended external names:

1. `Format Compliance Probe`
2. `Instruction Boundary Probe`
3. `Information Density Probe`
4. `Capability Behavior Probe`
5. `Style and Expression Probe`

These names should each have localized display strings.

Prompt summaries should stay half-explanatory, for example:

- `Structured output parsed successfully`
- `Instruction-following features extracted`
- `Timed out while waiting for response`
- `Response could not be parsed`

### 8. Final Result State

When all five prompts complete, the page can show a formal conclusion.

Required result sections:

- one-sentence conclusion card
- three compact metric cards:
  - similarity / match score
  - confidence interval
  - completed prompt count
- ranked nearby candidate models
- five-prompt review

If the selected fingerprint model is not the closest match, the selected model should still appear in the ranked list with a visible marker such as `Selected fingerprint`.

### 9. Result Language Rules

Formal result language is only allowed when all five prompts complete and no higher-priority exception state applies.

Allowed formal expressions:

- `likely is`
- `likely is not`
- confidence interval statements

If the selected fingerprint is not the closest match, the page should say the model is more similar to another known model.

### 10. Error Model

The page must not collapse every abnormal outcome into one generic failure state. The UI should separate:

1. startup/configuration error
2. single-prompt failure while the run continues
3. insufficient evidence
4. incompatible protocol
5. user-stopped run

### 11. Startup / Configuration Error

This means the run never really started.

Typical causes:

- invalid API key
- unreachable base URL
- missing or unknown model
- endpoint rejected the request shape before the five-prompt run began

UI rules:

- show an error card in the workbench
- do not render a five-prompt progress table as if a run is active
- keep the left column editable
- provide a retry action

### 12. Single-Prompt Failure While Run Continues

A prompt failure must not be treated as a whole-run failure if the system continues.

UI rules:

- keep the run in `running`
- show failed prompt count in the global status card
- keep the failed prompt visible in the prompt list
- display a short failure label such as:
  - `Authentication failed`
  - `Endpoint unreachable`
  - `Response timed out`
  - `Response could not be parsed`
- show a gentle explanatory message:
  - `Some prompts did not return usable results. The run will continue with the evidence available.`

### 13. Insufficient Evidence

This state means the run ended without enough usable evidence for a formal conclusion.

Decision rule:

- if completed prompt count is `0`, `1`, or `2`, show `Insufficient Evidence`

UI rules:

- show no formal identity judgment
- show no candidate ranking
- explain that the data is not sufficient to judge whether the model matches the selected fingerprint
- show suggested checks:
  - API key
  - base URL compatibility
  - model name validity
  - upstream timeout or rate limiting

### 14. Provisional Observation

This state applies when some meaningful evidence exists but the run is still incomplete.

Decision rule:

- if completed prompt count is `3` or `4`, and no higher-priority state applies, show `Provisional Observation`

UI rules:

- do not use formal verdict language such as `likely is` or `likely is not`
- do allow language such as:
  - `currently looks closer to`
  - `partial evidence suggests`
  - `provisional observation`
- allow a reduced candidate view with only cautious language

This preserves usefulness without overstating certainty.

### 15. Incompatible Protocol

This state must outrank provisional observation.

Meaning:

- the endpoint behavior did not stably satisfy required response/protocol expectations
- this is not the same as a model-identity mismatch

UI rules:

- show a dedicated protocol compatibility card
- explicitly state that the run cannot form a reliable comparison result
- explicitly state that this does not prove the model is not the claimed model
- do not show provisional observation or identity verdict text in this state

Priority rule:

- `incompatible protocol` overrides `provisional observation`

### 16. User-Stopped Run

If the user stops a run manually:

- do not style it as a system error
- show a neutral stopped state
- retain completed prompt rows and logs
- offer `Start New Check`

### 17. Final State Priority

The top-level workbench state should be decided in this order:

1. startup failed -> `Configuration Error`
2. user stopped -> `Stopped`
3. incompatible protocol -> `Incompatible Protocol`
4. completed prompts `< 3` -> `Insufficient Evidence`
5. completed prompts `3` or `4` -> `Provisional Observation`
6. completed prompts `5` -> `Formal Conclusion`

This ordering prevents contradictory UI.

### 18. Internationalization

Supported languages:

- English
- Simplified Chinese
- Japanese

Detection rules:

- if system locale matches `zh-CN`, use Simplified Chinese
- if system locale matches `ja`, use Japanese
- otherwise default to English

The UI must still expose a manual language switcher:

- `EN`
- `简中`
- `日本語`

All status labels, buttons, errors, and result templates must be sourced from translation keys rather than inline hard-coded strings.

Text-length implications:

- buttons must stay short
- cards must support multiline titles and body copy
- conclusion cards must allow natural wrapping

### 19. Theme Support

The page must support:

- `Light`
- `Dark`
- `System`

Recommended implementation shape:

- CSS variables for color tokens
- `next-themes` or equivalent system-theme wiring
- theme changes update presentation only and never reset run state

Visual direction:

- light mode first
- soft gray / slate / blue palette
- subtle paper-lab texture or grid feeling
- restrained borders and light shadows
- no purple bias
- no oversized gradients
- no 3D illustration style

### 20. Component System

The page must use official `shadcn/ui` components and official `lucide-react` icon usage only.

Recommended component mapping:

- top bar
  - `Button`
  - `DropdownMenu`
- configuration panel
  - `Card`
  - `Input`
  - `Select`
  - `Button`
  - `Alert`
- workbench
  - `Card`
  - `Badge`
  - `Progress`
  - `Table`
  - `Collapsible`
  - `Skeleton`
- stop confirmation
  - `AlertDialog`

Recommended icon semantics:

- brand / detection
  - scan / search / experiment motif
- language switcher
  - language icon
- theme switcher
  - sun / moon / monitor
- running
  - spinner / loader icon
- success
  - check icon
- waiting
  - clock icon
- warning / protocol issue
  - alert icon
- log toggle
  - chevron icon

Do not mix icon families.

### 21. Frontend / Backend Interaction Model

The browser should not orchestrate the five prompts itself. The backend should own execution.

Recommended flow:

1. frontend starts a run
2. backend returns a `run_id`
3. frontend polls run state
4. backend reports prompt-level progress and final result

Minimum frontend-facing fields:

- run status
- completed prompt count
- total prompt count
- current prompt name
- ETA
- prompt list with per-prompt status, elapsed time, summary, and error code
- result object with:
  - verdict or output state
  - selected fingerprint
  - top candidates when allowed
  - similarity / confidence data when allowed
  - failure reason when relevant

Error reporting should prefer machine-readable error codes plus localized frontend strings.

### 22. Copy Principles

The UI copy should follow these rules:

- never overstate certainty
- explain whether the issue is:
  - configuration
  - runtime
  - evidence sufficiency
  - protocol compatibility
- make the next operator action obvious
- preserve technical credibility for developer audiences

### 23. Non-Goals

- No homepage marketing narrative for the MVP.
- No user account system.
- No historical run dashboard in this phase.
- No promise that refreshing or leaving the page will preserve an in-flight run unless a backend run-resume contract is later added.
- No raw provider error dump as the primary UI.

## Outcome

The approved MVP is a single-page, two-column, research-tool-style detection console with:

- a left-side configuration panel
- a right-side live workbench
- formal conclusions only on complete five-prompt runs
- provisional observation for `3/5` or `4/5` usable prompts
- insufficient evidence for fewer than three usable prompts
- a separate incompatible-protocol state
- first-class internationalization and theme support
- official `shadcn/ui` and `lucide-react` usage throughout
