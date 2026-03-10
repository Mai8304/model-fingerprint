import { AlertTriangle, FlaskConical, ShieldAlert, StopCircle, CheckCircle2 } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
  empty: "border-slate-200 bg-slate-50 text-slate-700",
  running: "border-sky-200 bg-sky-50 text-sky-900",
  formal_result: "border-emerald-200 bg-emerald-50 text-emerald-900",
  provisional: "border-amber-200 bg-amber-50 text-amber-900",
  insufficient_evidence: "border-amber-200 bg-amber-50 text-amber-900",
  incompatible_protocol: "border-rose-200 bg-rose-50 text-rose-900",
  configuration_error: "border-rose-200 bg-rose-50 text-rose-900",
  stopped: "border-slate-300 bg-slate-100 text-slate-800",
} as const

export function ResultCard({ state }: { state: WorkbenchState }) {
  const Icon = iconByState[state.kind]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Result</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`rounded-2xl border px-4 py-4 ${toneByState[state.kind]}`}>
          <div className="flex items-start gap-3">
            <Icon className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="space-y-1">
              <p className="text-sm font-semibold">{state.title}</p>
              <p className="text-sm leading-6">{state.description}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
