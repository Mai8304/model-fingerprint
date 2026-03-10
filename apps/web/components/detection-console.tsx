"use client"

import { FlaskConical } from "lucide-react"

import { CheckConfigForm } from "@/components/check-config-form"
import { ResultCard } from "@/components/workbench/result-card"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TopBar } from "@/components/top-bar"
import { useLocale } from "@/lib/i18n/provider"
import type { CheckConfigValues } from "@/lib/check-config-schema"
import { deriveWorkbenchState } from "@/lib/run-state"

export function DetectionConsole() {
  const { t } = useLocale()
  const handleSubmit = (_values: CheckConfigValues) => undefined
  const workbenchState = deriveWorkbenchState({
    status: "idle",
    completedPrompts: 0,
    totalPrompts: 5,
    incompatibleProtocol: false,
    stoppedByUser: false,
    selectedFingerprint: "gpt-4.1-mini",
  })

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <TopBar />

      <div className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
        <Card aria-label="Configuration" role="region">
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <CheckConfigForm disabled={false} onSubmit={handleSubmit} />
          </CardContent>
        </Card>

        <div aria-label="Workbench" className="grid gap-4" role="region">
          <Card>
            <CardHeader>
              <CardTitle>Workbench</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center gap-3">
                  <FlaskConical className="h-5 w-5 text-sky-700" />
                  <div>
                    <p className="text-sm font-medium text-slate-900">No active check</p>
                    <p className="text-sm text-slate-600">
                      Enter endpoint details, choose a fingerprint model, and start a live five-prompt check.
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 p-4 text-sm text-slate-600">
                This panel will render the global run state, current probe, per-prompt status, and result conclusion.
              </div>
            </CardContent>
          </Card>

          <ResultCard state={workbenchState} />
        </div>
      </div>
    </div>
  )
}
