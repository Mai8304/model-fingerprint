"use client"

import { getPromptLabel } from "@/lib/prompt-copy"
import { useLocale } from "@/lib/i18n/provider"
import type { RunSnapshot } from "@/lib/run-types"

function metric(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "-"
  }
  if (typeof value === "boolean") {
    return value ? "yes" : "no"
  }
  return String(value)
}

export function PromptDiagnosticsTable({ run }: { run: RunSnapshot }) {
  const { locale } = useLocale()

  return (
    <section className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-950">Prompt Diagnostics</h3>
        <p className="text-xs uppercase tracking-[0.12em] text-slate-500">
          {run.completedPrompts} / {run.totalPrompts}
        </p>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-[0.12em] text-slate-500">
              <th className="border-b border-slate-200 px-3 py-2">Prompt</th>
              <th className="border-b border-slate-200 px-3 py-2">Status</th>
              <th className="border-b border-slate-200 px-3 py-2">Elapsed</th>
              <th className="border-b border-slate-200 px-3 py-2">First Byte</th>
              <th className="border-b border-slate-200 px-3 py-2">HTTP</th>
              <th className="border-b border-slate-200 px-3 py-2">Error</th>
              <th className="border-b border-slate-200 px-3 py-2">Finish</th>
              <th className="border-b border-slate-200 px-3 py-2">Bytes</th>
              <th className="border-b border-slate-200 px-3 py-2">Parse</th>
              <th className="border-b border-slate-200 px-3 py-2">Scoreable</th>
            </tr>
          </thead>
          <tbody>
            {run.prompts.length === 0 ? (
              <tr>
                <td className="px-3 py-4 text-sm text-slate-500" colSpan={10}>
                  No prompt data yet.
                </td>
              </tr>
            ) : (
              run.prompts.map((prompt) => {
                const isCurrent = prompt.prompt_id === run.currentPromptId
                return (
                  <tr
                    key={prompt.prompt_id}
                    className={isCurrent ? "bg-sky-50/70" : undefined}
                  >
                    <td className="border-b border-slate-100 px-3 py-3 align-top">
                      <div className="font-medium text-slate-900">{prompt.prompt_id}</div>
                      <div className="text-xs text-slate-500">
                        {getPromptLabel(prompt.prompt_id, locale)}
                      </div>
                      {prompt.error_detail ? (
                        <div className="mt-2 max-w-[260px] text-xs leading-5 text-slate-500">
                          {prompt.error_detail}
                        </div>
                      ) : null}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 align-top">{metric(prompt.status)}</td>
                    <td className="border-b border-slate-100 px-3 py-3 align-top">{metric(prompt.elapsed_ms === null ? null : `${prompt.elapsed_ms}ms`)}</td>
                    <td className="border-b border-slate-100 px-3 py-3 align-top">{metric(prompt.first_byte_ms === null ? null : `${prompt.first_byte_ms}ms`)}</td>
                    <td className="border-b border-slate-100 px-3 py-3 align-top">{metric(prompt.http_status)}</td>
                    <td className="border-b border-slate-100 px-3 py-3 align-top">{metric(prompt.error_code ?? prompt.error_kind)}</td>
                    <td className="border-b border-slate-100 px-3 py-3 align-top">{metric(prompt.finish_reason)}</td>
                    <td className="border-b border-slate-100 px-3 py-3 align-top">{metric(prompt.bytes_received)}</td>
                    <td className="border-b border-slate-100 px-3 py-3 align-top">{metric(prompt.parse_status)}</td>
                    <td className="border-b border-slate-100 px-3 py-3 align-top">{metric(prompt.scoreable)}</td>
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
