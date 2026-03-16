"use client"

import { useEffect, useEffectEvent, useMemo, useState } from "react"
import { ArrowRight, CheckCircle2, Fingerprint, FlaskConical } from "lucide-react"

import { CheckConfigForm } from "@/components/check-config-form"
import {
  ConclusionPanel,
  DetailedDiagnosticsPanel,
} from "@/components/workbench/conclusion-panel"
import { CapabilityProbePanel } from "@/components/workbench/capability-probe-panel"
import { PromptDiagnosticsTable } from "@/components/workbench/prompt-diagnostics-table"
import { SimilarModelsPanel } from "@/components/workbench/similar-models-panel"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TopBar } from "@/components/top-bar"
import { ApiClientError, cancelRun, createRun, getRun, getRunResult, listFingerprintModels } from "@/lib/api-client"
import { useLocale } from "@/lib/i18n/provider"
import type { CheckConfigValues } from "@/lib/check-config-schema"
import { deriveRemoteFieldErrors } from "@/lib/error-presentation"
import { fingerprintOptions as fallbackFingerprintOptions } from "@/lib/fingerprint-options"
import type {
  FingerprintOption,
  RunResultResource,
  RunResource,
  RunSnapshot,
} from "@/lib/run-types"
import { projectRunSnapshot } from "@/lib/run-state"

function resolveErrorMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    return {
      code: error.code as RunSnapshot["failureCode"],
      message: error.message,
    }
  }

  if (error instanceof Error) {
    return {
      code: undefined,
      message: error.message,
    }
  }

  return {
    code: undefined,
    message: "request failed",
  }
}

export function DetectionConsole() {
  const { locale, t } = useLocale()
  const [availableFingerprints, setAvailableFingerprints] = useState<FingerprintOption[]>(
    fallbackFingerprintOptions,
  )
  const [remoteSnapshot, setRemoteSnapshot] = useState<RunResource | null>(null)
  const [terminalResult, setTerminalResult] = useState<RunResultResource | null>(null)
  const [clientFailure, setClientFailure] = useState<string | null>(null)
  const [clientFailureCode, setClientFailureCode] = useState<RunSnapshot["failureCode"] | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const projectedRun = useMemo(
    () =>
      projectRunSnapshot(remoteSnapshot, terminalResult, {
        locale,
        failureReason: clientFailure,
        failureCode: clientFailureCode,
      }),
    [clientFailure, clientFailureCode, locale, remoteSnapshot, terminalResult],
  )
  const runIsActive =
    projectedRun.status === "validating" || projectedRun.status === "running"
  const remoteFieldErrors = useMemo(
    () => deriveRemoteFieldErrors(projectedRun, locale),
    [locale, projectedRun],
  )

  useEffect(() => {
    document.title = t("app.title")

    const description = document.querySelector('meta[name="description"]')
    if (description instanceof HTMLMetaElement) {
      description.content = t("app.subtitle")
    }
  }, [t])

  useEffect(() => {
    let cancelled = false

    async function loadFingerprints() {
      try {
        const items = await listFingerprintModels()
        if (cancelled) {
          return
        }
        setAvailableFingerprints(
          items.map((item) => ({
            value: item.id,
            label: item.label,
          })),
        )
      } catch {
        if (cancelled) {
          return
        }
        setAvailableFingerprints(fallbackFingerprintOptions)
      }
    }

    void loadFingerprints()

    return () => {
      cancelled = true
    }
  }, [])

  const syncRemoteState = useEffectEvent(
    (snapshot: RunResource | null, result: RunResultResource | null) => {
      setRemoteSnapshot(snapshot)
      setTerminalResult(result)
      setClientFailure(null)
      setClientFailureCode(null)
    },
  )

  const loadTerminalResult = useEffectEvent(async (snapshot: RunResource) => {
    try {
      const result = await getRunResult(snapshot.run_id)
      syncRemoteState(snapshot, result)
      return true
    } catch (error) {
      if (error instanceof ApiClientError && error.code === "RUN_NOT_COMPLETED") {
        syncRemoteState(snapshot, null)
        return false
      }

      const resolvedError = resolveErrorMessage(error)
      setClientFailure(resolvedError.message)
      setClientFailureCode(resolvedError.code)
      return false
    }
  })

  const pollRun = useEffectEvent(async (runId: string) => {
    try {
      const snapshot = await getRun(runId)

      if (snapshot.run_status === "completed") {
        const resolved = await loadTerminalResult(snapshot)
        if (!resolved) {
          syncRemoteState(snapshot, null)
        }
        return
      }

      syncRemoteState(snapshot, null)
    } catch (error) {
      const resolvedError = resolveErrorMessage(error)
      setClientFailure(resolvedError.message)
      setClientFailureCode(resolvedError.code)
    }
  })

  useEffect(() => {
    if (remoteSnapshot === null) {
      return
    }

    const shouldPoll =
      remoteSnapshot.run_status === "validating" ||
      remoteSnapshot.run_status === "running" ||
      (remoteSnapshot.run_status === "completed" &&
        terminalResult === null &&
        remoteSnapshot.result_state !== "configuration_error" &&
        remoteSnapshot.result_state !== "stopped")

    if (!shouldPoll) {
      return
    }

    const timer = window.setTimeout(() => {
      void pollRun(remoteSnapshot.run_id)
    }, 1000)

    return () => {
      window.clearTimeout(timer)
    }
  }, [pollRun, remoteSnapshot, terminalResult])

  async function handleSubmit(values: CheckConfigValues) {
    setIsSubmitting(true)
    setClientFailure(null)
    setClientFailureCode(null)
    setRemoteSnapshot(null)
    setTerminalResult(null)

    try {
      const created = await createRun({
        apiKey: values.apiKey,
        baseUrl: values.baseUrl,
        modelName: values.modelName,
        fingerprintModelId: values.fingerprintModel,
      })
      const snapshot = await getRun(created.run_id)

      if (snapshot.run_status === "completed") {
        const resolved = await loadTerminalResult(snapshot)
        if (!resolved) {
          syncRemoteState(snapshot, null)
        }
      } else {
        syncRemoteState(snapshot, null)
      }
    } catch (error) {
      const resolvedError = resolveErrorMessage(error)
      setRemoteSnapshot(null)
      setTerminalResult(null)
      setClientFailure(resolvedError.message)
      setClientFailureCode(resolvedError.code)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleCancel() {
    if (remoteSnapshot === null) {
      return
    }

    try {
      const cancelled = await cancelRun(remoteSnapshot.run_id)
      setRemoteSnapshot((current) => {
        if (current === null || current.run_id !== cancelled.run_id) {
          return current
        }

        return {
          ...current,
          cancel_requested: cancelled.cancel_requested,
        }
      })
    } catch (error) {
      const resolvedError = resolveErrorMessage(error)
      setClientFailure(resolvedError.message)
      setClientFailureCode(resolvedError.code)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <TopBar />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-6">
          <Card aria-label={t("sections.configuration")} role="region">
            <CardHeader>
              <CardTitle>{t("sections.configuration")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CheckConfigForm
                disabled={isSubmitting || runIsActive}
                fingerprintOptions={availableFingerprints}
                remoteErrors={remoteFieldErrors}
                onSubmit={handleSubmit}
              />
            </CardContent>
          </Card>
        </div>

        <Card aria-label={t("sections.result")} className="min-w-0 overflow-hidden" role="region">
          <CardHeader>
            <CardTitle>{t("sections.result")}</CardTitle>
          </CardHeader>
          <CardContent className="grid min-w-0 gap-6" data-testid="result-workbench">
            <ConclusionPanel run={projectedRun} />
            <CapabilityProbePanel run={projectedRun} />
            <PromptDiagnosticsTable run={projectedRun} />
            <DetailedDiagnosticsPanel run={projectedRun} />
            <SimilarModelsPanel run={projectedRun} />
            {runIsActive ? (
              <Button onClick={() => void handleCancel()} variant="outline">
                {t("actions.stopCheck")}
              </Button>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <Card aria-label={t("sections.howItWorks")} role="region">
        <CardHeader className="space-y-2">
          <CardTitle>{t("sections.howItWorks")}</CardTitle>
          <p className="max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            {t("howItWorks.intro")}
          </p>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-stretch" data-testid="how-it-works-flow">
            <div className="flex-1 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/60">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300">
                <Fingerprint className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
                {t("howItWorks.training.title")}
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {t("howItWorks.training.description")}
              </p>
            </div>

            <div
              aria-hidden="true"
              className="hidden items-center justify-center px-1 text-slate-300 dark:text-slate-700 lg:flex"
            >
              <ArrowRight className="h-4 w-4" />
            </div>

            <div className="flex-1 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/60">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300">
                <FlaskConical className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
                {t("howItWorks.comparison.title")}
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {t("howItWorks.comparison.description")}
              </p>
            </div>

            <div
              aria-hidden="true"
              className="hidden items-center justify-center px-1 text-slate-300 dark:text-slate-700 lg:flex"
            >
              <ArrowRight className="h-4 w-4" />
            </div>

            <div className="flex-1 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/60">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
                {t("howItWorks.conclusion.title")}
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {t("howItWorks.conclusion.description")}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
