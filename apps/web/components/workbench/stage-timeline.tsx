"use client"

import type { RunSnapshot, RunStageResource } from "@/lib/run-types"

function toneForStage(stage: RunStageResource) {
  switch (stage.status) {
    case "completed":
      return "border-emerald-200 bg-emerald-50 text-emerald-900"
    case "running":
      return "border-sky-200 bg-sky-50 text-sky-900"
    case "failed":
      return "border-rose-200 bg-rose-50 text-rose-900"
    default:
      return "border-slate-200 bg-white text-slate-700"
  }
}

export function StageTimeline({ run }: { run: RunSnapshot }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-950">Stage Timeline</h3>
        <p className="text-xs uppercase tracking-[0.12em] text-slate-500">
          {run.currentStageId ?? "not started"}
        </p>
      </div>

      <div className="mt-4 grid gap-3">
        {run.stages.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-4 text-sm text-slate-500">
            No stage data yet.
          </div>
        ) : (
          run.stages.map((stage) => (
            <div
              key={stage.id}
              className={`rounded-2xl border px-4 py-3 ${toneForStage(stage)}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-semibold">{stage.id}</div>
                <div className="text-xs uppercase tracking-[0.12em]">{stage.status}</div>
              </div>
              <p className="mt-2 text-sm leading-6">{stage.message ?? "No detail."}</p>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
