"use client"

import { AlertTriangle, FlaskConical, ShieldAlert, StopCircle, CheckCircle2 } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useLocale } from "@/lib/i18n/provider"
import type { WorkbenchState } from "@/lib/run-types"

const iconByState = {
  empty: FlaskConical,
  running: FlaskConical,
  formal_result: CheckCircle2,
  provisional: AlertTriangle,
  insufficient_evidence: AlertTriangle,
  incompatible_protocol: ShieldAlert,
  configuration_error: AlertTriangle,
  stopped: StopCircle,
} as const

const toneByState = {
  empty: "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-200",
  running: "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900/60 dark:bg-sky-950/35 dark:text-sky-100",
  formal_result:
    "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/35 dark:text-emerald-100",
  provisional:
    "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/35 dark:text-amber-100",
  insufficient_evidence:
    "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/35 dark:text-amber-100",
  incompatible_protocol:
    "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/35 dark:text-rose-100",
  configuration_error:
    "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/35 dark:text-rose-100",
  stopped: "border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-200",
} as const

function ResultCardBody({ state }: { state: WorkbenchState }) {
  const Icon = iconByState[state.kind]

  return (
    <div className={`rounded-2xl border px-4 py-4 ${toneByState[state.kind]}`}>
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-5 w-5 shrink-0" />
        <div className="space-y-1">
          <p className="text-sm font-semibold">{state.title}</p>
          <p className="text-sm leading-6">{state.description}</p>
          {state.totalPrompts !== undefined ? (
            <div className="flex flex-wrap items-center gap-2 pt-2 text-xs font-semibold uppercase tracking-[0.12em]">
              <span>{state.completedPrompts ?? 0} / {state.totalPrompts}</span>
              {state.currentPromptLabel ? <span>{state.currentPromptLabel}</span> : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export function ResultCard({
  state,
  embedded = false,
}: {
  state: WorkbenchState
  embedded?: boolean
}) {
  const { t } = useLocale()

  if (embedded) {
    return <ResultCardBody state={state} />
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("sections.result")}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResultCardBody state={state} />
      </CardContent>
    </Card>
  )
}
