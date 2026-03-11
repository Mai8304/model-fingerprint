"use client"

import type { RunSnapshot } from "@/lib/run-types"

function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "-"
  }
  return value.toFixed(3)
}

function KeyValueRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[180px_minmax(0,1fr)] gap-3 border-t border-slate-100 py-2 first:border-t-0 first:pt-0">
      <div className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">{label}</div>
      <div className="text-sm text-slate-900">{value}</div>
    </div>
  )
}

function RunningPanel({ run }: { run: RunSnapshot }) {
  return (
    <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-4 text-sky-950">
      <h3 className="text-sm font-semibold">Running Diagnostics</h3>
      <p className="mt-2 text-sm leading-6">
        Stage: {run.currentStageId ?? "pending"}.
        {" "}
        {run.currentStageMessage ?? "Waiting for fresh runtime state."}
      </p>
    </div>
  )
}

function ConfigurationErrorPanel({ run }: { run: RunSnapshot }) {
  return (
    <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-rose-950">
      <h3 className="text-sm font-semibold">Configuration Error</h3>
      <p className="mt-2 text-sm leading-6">{run.failureReason ?? "The run failed before prompt execution."}</p>
      <div className="mt-3 grid gap-2 text-sm">
        <div>Code: {run.failureCode ?? "-"}</div>
        <div>Field: {run.failureField ?? "-"}</div>
        <div>Stage: {run.currentStageId ?? "-"}</div>
      </div>
    </div>
  )
}

function InsufficientEvidencePanel({ run }: { run: RunSnapshot }) {
  const result = run.result
  return (
    <div className="grid gap-4">
      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-amber-950">
        <h3 className="text-sm font-semibold">Insufficient Evidence</h3>
        <p className="mt-2 text-sm leading-6">
          Formal verdict is blocked because the run did not produce enough scoreable evidence.
        </p>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
        <h4 className="text-sm font-semibold text-slate-950">Blocking Reasons</h4>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
          {(result?.diagnostics.blocking_reasons ?? []).map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
        <h4 className="text-sm font-semibold text-slate-950">Recommendations</h4>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
          {(result?.diagnostics.recommendations ?? []).map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function FinalResultPanel({ run }: { run: RunSnapshot }) {
  const result = run.result

  return (
    <div className="grid gap-4">
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-emerald-950">
        <h3 className="text-sm font-semibold">
          {result?.result_state === "formal_result" ? "Formal Conclusion" : "Detailed Result"}
        </h3>
        <p className="mt-2 text-sm leading-6">
          Verdict: {result?.verdict ?? "-"}.
          {" "}
          Claimed similarity {formatScore(result?.summary?.similarity_score)}.
          {" "}
          Top candidate {result?.summary?.top_candidate_label ?? "-"} @ {formatScore(result?.summary?.top_candidate_similarity)}.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
        <h4 className="text-sm font-semibold text-slate-950">Comparison Metrics</h4>
        <div className="mt-3">
          <KeyValueRow label="Selected Fingerprint" value={run.selectedFingerprint} />
          <KeyValueRow label="Top Candidate" value={result?.summary?.top_candidate_label ?? "-"} />
          <KeyValueRow label="Claimed Similarity" value={formatScore(result?.summary?.similarity_score)} />
          <KeyValueRow label="Margin" value={formatScore(result?.summary?.margin)} />
          <KeyValueRow label="Consistency" value={formatScore(result?.summary?.consistency)} />
          <KeyValueRow label="Protocol Status" value={result?.coverage?.protocol_status ?? "-"} />
          <KeyValueRow label="Answer Coverage" value={formatScore(result?.coverage?.answer_coverage_ratio)} />
          <KeyValueRow label="Reasoning Coverage" value={formatScore(result?.coverage?.reasoning_coverage_ratio)} />
          <KeyValueRow label="Capability Similarity" value={formatScore(result?.dimensions?.capability_similarity)} />
          <KeyValueRow label="Content Similarity" value={formatScore(result?.dimensions?.content_similarity)} />
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
        <h4 className="text-sm font-semibold text-slate-950">Top Candidates</h4>
        <div className="mt-3 space-y-2 text-sm text-slate-700">
          {(result?.candidates ?? []).map((candidate) => (
            <div
              key={candidate.model_id}
              className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 px-3 py-2"
            >
              <span>{candidate.label}</span>
              <span className="font-medium text-slate-900">{formatScore(candidate.similarity)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
        <h4 className="text-sm font-semibold text-slate-950">Diagnostics</h4>
        <div className="mt-3 grid gap-3">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Protocol Issues</div>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {(result?.diagnostics.protocol_issues ?? []).map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Hard Mismatches</div>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {(result?.diagnostics.hard_mismatches ?? []).map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export function ConclusionPanel({ run }: { run: RunSnapshot }) {
  if (run.status === "idle") {
    return (
      <section className="rounded-2xl border border-dashed border-slate-200 px-4 py-4 text-sm text-slate-500">
        Run conclusion and diagnostics report will appear here after execution starts.
      </section>
    )
  }

  if (run.status === "validating" || run.status === "running") {
    return <RunningPanel run={run} />
  }

  if (run.status === "stopped" || run.resultState === "stopped") {
    return (
      <section className="rounded-2xl border border-slate-300 bg-slate-100 px-4 py-4 text-slate-900">
        <h3 className="text-sm font-semibold">Check Stopped</h3>
        <p className="mt-2 text-sm leading-6">
          This run was stopped before enough evidence was collected for a final conclusion.
        </p>
      </section>
    )
  }

  if (run.resultState === "configuration_error") {
    return <ConfigurationErrorPanel run={run} />
  }

  if (run.resultState === "insufficient_evidence") {
    return <InsufficientEvidencePanel run={run} />
  }

  return <FinalResultPanel run={run} />
}
