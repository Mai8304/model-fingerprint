"use client"

import type { ReactNode } from "react"

import { formatWorkbench, getWorkbenchCopy } from "@/components/workbench/copy"
import {
  formatPromptNotScoreableReason,
  formatPromptReason,
  localizeDiagnosticText,
} from "@/components/workbench/diagnostic-localization"
import { useLocale } from "@/lib/i18n/provider"
import type { LocaleKey } from "@/lib/i18n/messages"
import { presentFailureMessage } from "@/lib/failure-presentation"
import type { RunResultResource, RunSnapshot } from "@/lib/run-types"

type FormalConclusionKind = "highlyConsistent" | "similar" | "mismatch" | "unknown"

function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "-"
  }
  return value.toFixed(3)
}

function formatRange(
  low: number | null | undefined,
  high: number | null | undefined,
  unavailable: string,
) {
  if (low === null || low === undefined || high === null || high === undefined) {
    return unavailable
  }
  return `${formatScore(low)} - ${formatScore(high)}`
}

function scoreableSummary(result: RunResultResource | null | undefined, totalPrompts: number) {
  if (result === null || result === undefined) {
    return "-"
  }
  const promptBreakdown = result.prompt_breakdown ?? []
  const scoreableCount = promptBreakdown.filter((prompt) => prompt.scoreable).length
  const promptCount = promptBreakdown.length === 0 ? totalPrompts : promptBreakdown.length
  return `${scoreableCount} / ${promptCount}`
}

function formatCandidateWithScore(
  copy: ReturnType<typeof getWorkbenchCopy>,
  label: string | null | undefined,
  score: number | null | undefined,
): ReactNode {
  if (label === null || label === undefined || label === "") {
    return copy.shared.unavailable
  }

  const scoreText = score === null || score === undefined ? null : formatScore(score)
  return (
    <>
      <strong className="font-semibold text-slate-950 dark:text-slate-50">{label}</strong>
      {scoreText === null ? null : ` (${scoreText})`}
    </>
  )
}

function capabilityDisplayName(
  copy: ReturnType<typeof getWorkbenchCopy>,
  capability: string,
) {
  if (capability === "image") {
    return copy.capabilityNames.image_generation
  }
  if (capability === "vision") {
    return copy.capabilityNames.vision_understanding
  }
  return copy.capabilityNames[capability] ?? capability
}

function renderSentenceWithBoldModel(template: string, model: string): ReactNode {
  const parts = template.split("{model}")
  if (parts.length === 1) {
    return template
  }

  return parts.flatMap((part, index) => {
    if (index === parts.length - 1) {
      return [part]
    }
    return [
      part,
      <strong
        key={`model-${index}`}
        className="font-semibold text-slate-950 dark:text-slate-50"
      >
        {model}
      </strong>,
    ]
  })
}

function deriveFormalKind(run: RunSnapshot): FormalConclusionKind | null {
  const result = run.result ?? null
  if (run.resultState !== "formal_result" || result === null || result.summary === null) {
    return null
  }

  const summary = result.summary
  if (summary.top_candidate_model_id === null || summary.top_candidate_model_id === undefined) {
    return "unknown"
  }

  if (summary.top_candidate_model_id === result.selected_fingerprint.id) {
    return summary.in_confidence_range === true ? "highlyConsistent" : "similar"
  }

  return result.verdict === "unknown" ? "unknown" : "mismatch"
}

function titleForConclusion(copy: ReturnType<typeof getWorkbenchCopy>, run: RunSnapshot) {
  const formalKind = deriveFormalKind(run)
  if (formalKind === "highlyConsistent") {
    return `✅ ${copy.conclusion.sectionTitle} · ${copy.conclusion.labels.highlyConsistent}`
  }
  if (formalKind === "similar") {
    return `🟢 ${copy.conclusion.sectionTitle} · ${copy.conclusion.labels.similar}`
  }
  if (formalKind === "mismatch") {
    return `❌ ${copy.conclusion.sectionTitle} · ${copy.conclusion.labels.mismatch}`
  }
  if (formalKind === "unknown") {
    return `❓ ${copy.conclusion.sectionTitle} · ${copy.conclusion.labels.unknown}`
  }
  if (run.status === "validating" || run.status === "running") {
    return copy.conclusion.labels.running
  }
  if (run.resultState === "configuration_error" || run.status === "configuration_error") {
    return copy.conclusion.labels.configurationError
  }
  if (run.resultState === "stopped" || run.status === "stopped") {
    return copy.conclusion.labels.stopped
  }
  if (run.resultState === "insufficient_evidence") {
    return copy.conclusion.labels.insufficientEvidence
  }
  if (run.resultState === "incompatible_protocol") {
    return copy.conclusion.labels.incompatibleProtocol
  }
  if (run.resultState === "provisional") {
    return copy.conclusion.labels.provisional
  }
  return copy.conclusion.sectionTitle
}

function toneForConclusion(run: RunSnapshot) {
  const formalKind = deriveFormalKind(run)
  if (formalKind === "highlyConsistent" || formalKind === "similar") {
    return "border-emerald-200 bg-emerald-50 dark:border-emerald-900/60 dark:bg-emerald-950/35"
  }
  if (formalKind === "mismatch") {
    return "border-rose-200 bg-rose-50 dark:border-rose-900/60 dark:bg-rose-950/35"
  }
  if (formalKind === "unknown" || run.resultState === "stopped" || run.status === "stopped") {
    return "border-slate-300 bg-slate-100 dark:border-slate-800 dark:bg-slate-900/70"
  }
  if (run.status === "validating" || run.status === "running") {
    return "border-sky-200 bg-sky-50 dark:border-sky-900/60 dark:bg-sky-950/35"
  }
  if (run.resultState === "configuration_error" || run.resultState === "incompatible_protocol") {
    return "border-rose-200 bg-rose-50 dark:border-rose-900/60 dark:bg-rose-950/35"
  }
  if (run.resultState === "insufficient_evidence" || run.resultState === "provisional") {
    return "border-amber-200 bg-amber-50 dark:border-amber-900/60 dark:bg-amber-950/35"
  }
  return "border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/70"
}

function conclusionMessage(
  copy: ReturnType<typeof getWorkbenchCopy>,
  locale: LocaleKey,
  run: RunSnapshot,
): ReactNode {
  const formalKind = deriveFormalKind(run)
  const selectedFingerprintLabel = run.result?.selected_fingerprint.label

  if (formalKind === "highlyConsistent") {
    return selectedFingerprintLabel
      ? renderSentenceWithBoldModel(copy.conclusion.firstSentence.highlyConsistent, selectedFingerprintLabel)
      : copy.conclusion.messages.highlyConsistent
  }
  if (formalKind === "similar") {
    return copy.conclusion.firstSentence.similar
  }
  if (formalKind === "mismatch") {
    return copy.conclusion.firstSentence.mismatch
  }
  if (formalKind === "unknown") {
    return copy.conclusion.firstSentence.unknown
  }
  if (run.status === "validating" || run.status === "running") {
    return copy.conclusion.messages.running
  }
  if (run.resultState === "configuration_error" || run.status === "configuration_error") {
    return presentFailureMessage({
      code: run.failureCode,
      message: run.failureReason,
      locale,
      fallback: copy.conclusion.messages.configurationError,
    })
  }
  if (run.resultState === "stopped" || run.status === "stopped") {
    return copy.conclusion.messages.stopped
  }
  if (run.resultState === "insufficient_evidence") {
    return copy.conclusion.messages.insufficientEvidence
  }
  if (run.resultState === "incompatible_protocol") {
    return copy.conclusion.messages.incompatibleProtocol
  }
  if (run.resultState === "provisional") {
    return copy.conclusion.firstSentence.provisional
  }
  return copy.conclusion.placeholder
}

function protocolStatus(
  copy: ReturnType<typeof getWorkbenchCopy>,
  status: string | null | undefined,
) {
  if (status === null || status === undefined) {
    return copy.shared.unavailable
  }
  return copy.protocolStatuses[status] ?? status
}

function rangeGapText(
  copy: ReturnType<typeof getWorkbenchCopy>,
  summary: RunResultResource["summary"],
) {
  if (summary === null) {
    return copy.range.unavailable
  }
  if (summary.range_gap === null || summary.range_gap === undefined) {
    return copy.range.unavailable
  }
  if (summary.in_confidence_range === true) {
    return copy.range.inside
  }
  if (
    summary.similarity_score !== null &&
    summary.similarity_score !== undefined &&
    summary.confidence_low !== null &&
    summary.confidence_low !== undefined &&
    summary.similarity_score < summary.confidence_low
  ) {
    return formatWorkbench(copy.range.below, { delta: formatScore(summary.range_gap) })
  }
  return formatWorkbench(copy.range.above, { delta: formatScore(summary.range_gap) })
}

function buildWhyGroups(
  copy: ReturnType<typeof getWorkbenchCopy>,
  locale: LocaleKey,
  run: RunSnapshot,
) {
  const result = run.result ?? null
  const summary = result?.summary
  const thresholds = result?.thresholds_used
  const rangeItems: string[] = []
  const capabilityItems: string[] = []
  const promptItems: string[] = []
  const strengthItems: string[] = []

  if (summary !== null && summary !== undefined) {
    const range = formatRange(summary.confidence_low, summary.confidence_high, copy.range.unavailable)
    if (summary.in_confidence_range === true) {
      rangeItems.push(formatWorkbench(copy.conclusion.patterns.rangeInside, { range }))
    } else if (summary.range_gap !== null && summary.range_gap !== undefined) {
      rangeItems.push(
        formatWorkbench(copy.conclusion.patterns.rangeDeviation, {
          gap: rangeGapText(copy, summary),
          range,
        }),
      )
    }
  }

  const capabilityComparisons = result?.capability_comparisons ?? []
  if (capabilityComparisons.length === 0) {
    capabilityItems.push(copy.capabilityProbe.empty)
  } else {
    for (const item of capabilityComparisons) {
      const observed = item.observed_status
        ? copy.capabilityProbe.statuses[item.observed_status] ?? item.observed_status
        : copy.shared.unavailable
      const expected = item.expected_status
        ? copy.capabilityProbe.statuses[item.expected_status] ?? item.expected_status
        : copy.shared.unavailable
      const consistency =
        item.is_consistent === true
          ? copy.capabilityProbe.consistency.yes
          : item.is_consistent === false
            ? copy.capabilityProbe.consistency.no
            : copy.capabilityProbe.consistency.unknown
      const capability = capabilityDisplayName(copy, item.capability)

      if (item.is_consistent === true) {
        capabilityItems.push(
          formatWorkbench(copy.conclusion.patterns.capabilityConsistent, {
            capability,
            consistency,
            status: observed === copy.shared.unavailable ? expected : observed,
          }),
        )
        continue
      }

      if (item.is_consistent === false) {
        capabilityItems.push(
          formatWorkbench(copy.conclusion.patterns.capabilityMismatch, {
            capability,
            consistency,
            observed,
            expected,
          }),
        )
        continue
      }

      capabilityItems.push(
        formatWorkbench(copy.conclusion.patterns.capabilityInsufficient, {
          capability,
          consistency,
        }),
      )
    }
  }

  const promptBreakdown = result?.prompt_breakdown ?? []
  const matchThreshold = thresholds?.match ?? 0.96
  for (const prompt of promptBreakdown) {
    const errorText = prompt.error_message ?? prompt.error_kind
    if (!prompt.scoreable) {
      promptItems.push(
        formatPromptNotScoreableReason({
          promptId: prompt.prompt_id,
          detail: errorText,
          locale,
          copy,
        }),
      )
      continue
    }
    if (prompt.similarity !== null && prompt.similarity < matchThreshold) {
      promptItems.push(
        formatPromptReason({
          promptId: prompt.prompt_id,
          similarity: formatScore(prompt.similarity),
          locale,
          copy,
        }),
      )
      continue
    }
    if (errorText) {
      promptItems.push(
        localizeDiagnosticText(`${prompt.prompt_id}: ${errorText}`, locale, copy),
      )
    }
  }
  if (promptItems.length === 0 && promptBreakdown.length > 0) {
    promptItems.push(copy.conclusion.patterns.promptAllClose)
  }

  for (const reason of result?.diagnostics.blocking_reasons ?? []) {
    strengthItems.push(localizeDiagnosticText(reason, locale, copy))
  }
  if (strengthItems.length === 0) {
    strengthItems.push(copy.conclusion.reasons.none)
  }

  return [
    { title: copy.conclusion.reasons.range, items: rangeItems.length > 0 ? rangeItems : [copy.range.unavailable] },
    { title: copy.conclusion.reasons.capabilities, items: capabilityItems },
    { title: copy.conclusion.reasons.prompts, items: promptItems.length > 0 ? promptItems : [copy.conclusion.reasons.none] },
    { title: copy.conclusion.reasons.strength, items: strengthItems },
  ]
}

function KeyValueRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="border-t border-slate-200 py-3 first:border-t-0 first:pt-0 dark:border-slate-800">
      <div className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
        {label}
      </div>
      <div className="mt-1 text-sm text-slate-900 dark:text-slate-100">{value}</div>
    </div>
  )
}

function keyEvidenceRows(copy: ReturnType<typeof getWorkbenchCopy>, run: RunSnapshot) {
  const result = run.result ?? null
  const summary = result?.summary
  const coverage = result?.coverage

  return [
    {
      label: copy.diagnostics.metrics.fingerprintRange,
      value: formatRange(summary?.confidence_low, summary?.confidence_high, copy.range.unavailable),
    },
    {
      label: copy.diagnostics.metrics.rangeGap,
      value: rangeGapText(copy, summary ?? null),
    },
    {
      label: copy.diagnostics.metrics.scoreablePrompts,
      value: scoreableSummary(result, run.totalPrompts),
    },
    {
      label: copy.diagnostics.metrics.protocolStatus,
      value: protocolStatus(copy, coverage?.protocol_status),
    },
  ]
}

function standaloneNearestCandidate(copy: ReturnType<typeof getWorkbenchCopy>, run: RunSnapshot) {
  const summary = run.result?.summary ?? null
  if (summary === null) {
    return null
  }
  if (deriveFormalKind(run) === "highlyConsistent") {
    return null
  }
  if (summary.top_candidate_label === null || summary.top_candidate_label === undefined) {
    return null
  }

  return {
    label: copy.diagnostics.metrics.topCandidate,
    value: formatCandidateWithScore(copy, summary.top_candidate_label, summary.top_candidate_similarity),
  }
}

function diagnosticEvidenceRows(copy: ReturnType<typeof getWorkbenchCopy>, run: RunSnapshot) {
  const summary = run.result?.summary ?? null

  return [
    {
      label: copy.diagnostics.metrics.fingerprintRange,
      value: formatRange(summary?.confidence_low, summary?.confidence_high, copy.range.unavailable),
    },
    {
      label: copy.diagnostics.metrics.rangeGap,
      value: rangeGapText(copy, summary),
    },
  ]
}

export function ConclusionPanel({ run }: { run: RunSnapshot }) {
  const { locale } = useLocale()
  const copy = getWorkbenchCopy(locale)
  const result = run.result ?? null
  const nearestCandidate = standaloneNearestCandidate(copy, run)

  return (
    <section className={`min-w-0 rounded-2xl border px-4 py-4 ${toneForConclusion(run)}`}>
      <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
        {titleForConclusion(copy, run)}
      </h3>
      <p className="mt-3 text-sm leading-6 text-slate-900 dark:text-slate-100">
        {conclusionMessage(copy, locale, run)}
      </p>

      {nearestCandidate === null ? null : (
        <div className="mt-4">
          <div className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
            {nearestCandidate.label}
          </div>
          <div className="mt-1 text-sm text-slate-900 dark:text-slate-100">
            {nearestCandidate.value}
          </div>
        </div>
      )}

      {result !== null ? (
        <>
          <div className="mt-5">
            <div className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
              {copy.conclusion.whyTitle}
            </div>
            <div className="mt-3 space-y-4">
              {buildWhyGroups(copy, locale, run).map((group) => (
                <div key={group.title}>
                  <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {group.title}
                  </div>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300">
                    {group.items.map((item) => (
                      <li key={`${group.title}:${item}`}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-5">
            <div className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
              {copy.conclusion.evidenceTitle}
            </div>
            <div className="mt-3">
              {keyEvidenceRows(copy, run).map((row) => (
                <KeyValueRow key={row.label} label={row.label} value={row.value} />
              ))}
            </div>
          </div>
        </>
      ) : null}
    </section>
  )
}

function DiagnosticSection({
  title,
  items,
  empty,
}: {
  title: string
  items: string[]
  empty: string
}) {
  return (
    <div className="border-t border-slate-200 pt-4 first:border-t-0 first:pt-0 dark:border-slate-800">
      <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{title}</div>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{empty}</p>
      ) : (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300">
          {items.map((item) => (
            <li key={`${title}:${item}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function DetailedDiagnosticsPanel({ run }: { run: RunSnapshot }) {
  const { locale } = useLocale()
  const copy = getWorkbenchCopy(locale)
  const result = run.result ?? null

  if (result === null) {
    return (
      <section className="min-w-0 rounded-2xl border border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900/70">
        <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
          {copy.diagnostics.title}
        </h3>
        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
          {copy.diagnostics.empty}
        </p>
      </section>
    )
  }

  const selectedProtocolIssues =
    (result.selected_candidate?.protocol_issues ?? result.diagnostics.protocol_issues ?? []).map((item) =>
      localizeDiagnosticText(item, locale, copy),
    )
  const selectedHardMismatches =
    (result.selected_candidate?.hard_mismatches ?? result.diagnostics.hard_mismatches ?? []).map(
      (item) => localizeDiagnosticText(item, locale, copy),
    )
  const blockingReasons = (result.diagnostics.blocking_reasons ?? []).map((item) =>
    localizeDiagnosticText(item, locale, copy),
  )
  const recommendations = (result.diagnostics.recommendations ?? []).map((item) =>
    localizeDiagnosticText(item, locale, copy),
  )

  return (
    <section className="min-w-0 rounded-2xl border border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900/70">
      <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
        {copy.diagnostics.title}
      </h3>

      <div className="mt-4">
        {diagnosticEvidenceRows(copy, run).map((row) => (
          <KeyValueRow key={row.label} label={row.label} value={row.value} />
        ))}
      </div>

      <div className="mt-5 space-y-4">
        <DiagnosticSection
          title={copy.diagnostics.sections.protocolIssues}
          items={selectedProtocolIssues}
          empty={copy.diagnostics.none}
        />
        <DiagnosticSection
          title={copy.diagnostics.sections.hardMismatches}
          items={selectedHardMismatches}
          empty={copy.diagnostics.none}
        />
        <DiagnosticSection
          title={copy.diagnostics.sections.blockingReasons}
          items={blockingReasons}
          empty={copy.diagnostics.none}
        />
        <DiagnosticSection
          title={copy.diagnostics.sections.recommendations}
          items={recommendations}
          empty={copy.diagnostics.none}
        />
      </div>
    </section>
  )
}
