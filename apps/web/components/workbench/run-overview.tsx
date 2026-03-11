"use client"

import { useLocale } from "@/lib/i18n/provider"
import type { RunSnapshot } from "@/lib/run-types"

function formatDateTime(value: string | undefined) {
  if (value === undefined) {
    return "-"
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function formatStatus(run: RunSnapshot) {
  if (run.status === "idle") {
    return "IDLE"
  }
  if (run.resultState === "configuration_error") {
    return "CONFIG_ERROR"
  }
  if (run.resultState === "insufficient_evidence") {
    return "INSUFFICIENT"
  }
  if (run.resultState === "formal_result") {
    return "FORMAL"
  }
  if (run.resultState === "provisional") {
    return "PROVISIONAL"
  }
  if (run.resultState === "incompatible_protocol") {
    return "INCOMPATIBLE"
  }
  return run.status.toUpperCase()
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[140px_minmax(0,1fr)] gap-3 border-t border-slate-100 py-2 first:border-t-0 first:pt-0">
      <dt className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">{label}</dt>
      <dd className="min-w-0 break-all text-sm text-slate-900">{value}</dd>
    </div>
  )
}

export function RunOverview({ run }: { run: RunSnapshot }) {
  const { t } = useLocale()

  if (run.runId === null) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
        <h3 className="text-sm font-semibold text-slate-950">Run Overview</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">{t("state.workbenchPlaceholder")}</p>
      </section>
    )
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">Run Overview</h3>
          <p className="mt-1 text-sm text-slate-600">
            Status: <span className="font-medium text-slate-900">{formatStatus(run)}</span>
          </p>
        </div>
        <div className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-700">
          {run.currentStageId ?? "completed"}
        </div>
      </div>

      <dl className="mt-4">
        <DetailRow label="Base URL" value={run.baseUrl ?? "-"} />
        <DetailRow label="Model" value={run.modelName ?? "-"} />
        <DetailRow label="Fingerprint" value={run.selectedFingerprint} />
        <DetailRow label="Run ID" value={run.runId} />
        <DetailRow label="Started" value={formatDateTime(run.createdAt)} />
        <DetailRow label="Updated" value={formatDateTime(run.updatedAt)} />
        <DetailRow label="Progress" value={`${run.completedPrompts} / ${run.totalPrompts}`} />
        <DetailRow label="Failures" value={String(run.failedPrompts)} />
        <DetailRow label="Current Prompt" value={run.currentPromptLabel ?? run.currentPromptId ?? "-"} />
        <DetailRow label="Stage Message" value={run.currentStageMessage ?? "-"} />
      </dl>
    </section>
  )
}
