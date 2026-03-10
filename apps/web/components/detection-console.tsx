"use client"

import { FlaskConical, Play, ShieldCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TopBar } from "@/components/top-bar"
import { useLocale } from "@/lib/i18n/provider"

export function DetectionConsole() {
  const { t } = useLocale()

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <TopBar />

      <div className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
        <Card aria-label="Configuration" role="region">
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <p className="text-sm font-medium text-slate-900">API Key</p>
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400">
                sk-********************************
              </div>
            </div>

            <div className="space-y-1">
              <p className="text-sm font-medium text-slate-900">Base URL</p>
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                https://api.example.com/v1
              </div>
            </div>

            <div className="space-y-1">
              <p className="text-sm font-medium text-slate-900">Model Name</p>
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                gpt-4.1-mini
              </div>
            </div>

            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <div className="flex items-start gap-3">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                <p>Your API key is used only for this check and is not stored after the request completes.</p>
              </div>
            </div>

            <Button className="w-full gap-2">
              <Play className="h-4 w-4" />
              {t("actions.startCheck")}
            </Button>
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
        </div>
      </div>
    </div>
  )
}
