"use client"

import { getWorkbenchCopy } from "@/components/workbench/copy"
import { defaultPromptIds, getPromptDisplayInfo } from "@/lib/prompt-copy"
import { useLocale } from "@/lib/i18n/provider"
import type { RunSnapshot } from "@/lib/run-types"

function formatScore(value: number | null | undefined, fallback: string) {
  if (value === null || value === undefined) {
    return fallback
  }
  return value.toFixed(3)
}

function yesNo(value: boolean | null | undefined, yes: string, no: string, fallback: string) {
  if (value === null || value === undefined) {
    return fallback
  }
  return value ? yes : no
}

function promptStatusLabel(
  status: string,
  labels: Record<string, string>,
) {
  return labels[status] ?? status
}

function getPromptFocus(
  promptId: string,
  locale: ReturnType<typeof useLocale>["locale"],
) {
  const display = getPromptDisplayInfo(promptId, locale)
  return display.focus ?? display.title
}

function buildPromptRows(
  run: RunSnapshot,
  locale: ReturnType<typeof useLocale>["locale"],
  copy: ReturnType<typeof getWorkbenchCopy>,
) {
  const livePrompts = new Map(run.prompts.map((prompt) => [prompt.prompt_id, prompt]))
  const terminalPrompts = new Map(
    (run.result?.prompt_breakdown ?? []).map((prompt) => [prompt.prompt_id, prompt]),
  )
  const promptIds = [
    ...run.prompts.map((prompt) => prompt.prompt_id),
    ...(run.result?.prompt_breakdown ?? []).map((prompt) => prompt.prompt_id),
  ]
  const orderedPromptIds =
    promptIds.length > 0
      ? Array.from(new Set(promptIds))
      : run.runId === null
        ? []
        : [...defaultPromptIds]

  return orderedPromptIds.map((promptId) => {
    const livePrompt = livePrompts.get(promptId) ?? null
    const terminalPrompt = terminalPrompts.get(promptId) ?? null
    const display = getPromptDisplayInfo(promptId, locale)
    const errorText =
      terminalPrompt?.error_message ??
      terminalPrompt?.error_kind ??
      livePrompt?.error_detail ??
      livePrompt?.error_kind ??
      livePrompt?.error_code ??
      copy.shared.unavailable
    const status = terminalPrompt?.status ?? livePrompt?.status ?? "pending"
    const similarity = terminalPrompt?.similarity ?? null
    const scoreable = terminalPrompt?.scoreable ?? livePrompt?.scoreable ?? null
    const summary =
      terminalPrompt === null
        ? livePrompt === null
          ? display.focus ?? display.title
          : getPromptFocus(promptId, locale)
        : display.focus ?? display.title

    return {
      promptId,
      title: display.title,
      stepLabel: display.stepLabel,
      status,
      similarity,
      scoreable,
      errorText,
      summary,
    }
  })
}

export function PromptDiagnosticsTable({ run }: { run: RunSnapshot }) {
  const { locale } = useLocale()
  const copy = getWorkbenchCopy(locale)
  const prompts = buildPromptRows(run, locale, copy)

  return (
    <section className="min-w-0 rounded-2xl border border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900/70">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
          {copy.promptProbe.title}
        </h3>
        <p className="text-xs uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
          {run.completedPrompts} / {run.totalPrompts}
        </p>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table
          className="w-full min-w-[720px] border-separate border-spacing-0 text-left text-sm"
          data-testid="prompt-probe-table"
        >
          <thead>
            <tr className="text-xs uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
              <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                {copy.promptProbe.columns.prompt}
              </th>
              <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                {copy.promptProbe.columns.status}
              </th>
              <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                {copy.promptProbe.columns.similarity}
              </th>
              <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                {copy.promptProbe.columns.scoreable}
              </th>
              <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                {copy.promptProbe.columns.error}
              </th>
              <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                {copy.promptProbe.columns.summary}
              </th>
            </tr>
          </thead>
          <tbody>
            {prompts.length === 0 ? (
              <tr>
                <td className="px-3 py-4 align-middle text-sm text-slate-500 dark:text-slate-400" colSpan={6}>
                  {copy.promptProbe.empty}
                </td>
              </tr>
            ) : (
              prompts.map((prompt) => {
                return (
                  <tr key={prompt.promptId}>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle dark:border-slate-800">
                      <div className="font-medium text-slate-900 dark:text-slate-100">{prompt.title}</div>
                      {prompt.stepLabel ? (
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                          {prompt.stepLabel}
                        </div>
                      ) : null}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                      {promptStatusLabel(prompt.status, copy.promptProbe.statuses)}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                      {formatScore(prompt.similarity, copy.shared.unavailable)}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                      {yesNo(prompt.scoreable, copy.shared.yes, copy.shared.no, copy.shared.unavailable)}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                      {prompt.errorText}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                      {prompt.summary}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
