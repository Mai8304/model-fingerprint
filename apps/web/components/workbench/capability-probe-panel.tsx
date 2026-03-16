"use client"

import { getWorkbenchCopy } from "@/components/workbench/copy"
import { useLocale } from "@/lib/i18n/provider"
import type { RunSnapshot } from "@/lib/run-types"

const defaultCapabilities = [
  "thinking",
  "tools",
  "streaming",
  "image_generation",
  "vision_understanding",
]

type CapabilityRow = {
  capability: string
  observed_status: string | null
  expected_status: string | null
  is_consistent: boolean | null
  live: boolean
}

function valueOrFallback(value: string | null | undefined, fallback: string) {
  if (value === null || value === undefined || value === "") {
    return fallback
  }
  return value
}

function parseCapabilityStatuses(message: string | null | undefined) {
  if (message === null || message === undefined || message === "") {
    return new Map<string, string>()
  }

  const matches = message.matchAll(/([a-z_]+)=([a-z_]+)/g)
  return new Map<string, string>(Array.from(matches, ([, capability, status]) => [capability, status]))
}

function deriveCapabilityRows(run: RunSnapshot): CapabilityRow[] {
  const resultComparisons = run.result?.capability_comparisons ?? []
  if (resultComparisons.length > 0) {
    return resultComparisons.map((comparison) => ({
      ...comparison,
      live: false,
    }))
  }

  if (run.status === "idle" || run.runId === null) {
    return []
  }

  const capabilityStage = run.stages.find((stage) => stage.id === "capability_probe")
  const parsedStatuses = parseCapabilityStatuses(capabilityStage?.message)
  const orderedCapabilities = [
    ...defaultCapabilities,
    ...Array.from(parsedStatuses.keys()).filter((capability) => !defaultCapabilities.includes(capability)),
  ]

  return orderedCapabilities.map((capability) => {
    if (parsedStatuses.has(capability)) {
      return {
        capability,
        observed_status: parsedStatuses.get(capability) ?? null,
        expected_status: null,
        is_consistent: null,
        live: true,
      }
    }

    const observedStatus =
      capabilityStage?.status === "running"
        ? "running"
        : capabilityStage?.status === "pending"
          ? "pending"
          : null

    return {
      capability,
      observed_status: observedStatus,
      expected_status: null,
      is_consistent: null,
      live: true,
    }
  })
}

export function CapabilityProbePanel({ run }: { run: RunSnapshot }) {
  const { locale } = useLocale()
  const copy = getWorkbenchCopy(locale)
  const comparisons = deriveCapabilityRows(run)

  return (
    <section className="min-w-0 rounded-2xl border border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900/70">
      <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
        {copy.capabilityProbe.title}
      </h3>

      {comparisons.length === 0 ? (
        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
          {copy.capabilityProbe.empty}
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  {copy.capabilityProbe.columns.capability}
                </th>
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  {copy.capabilityProbe.columns.observed}
                </th>
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  {copy.capabilityProbe.columns.expected}
                </th>
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  {copy.capabilityProbe.columns.consistent}
                </th>
              </tr>
            </thead>
            <tbody>
              {comparisons.map((comparison) => {
                const observed =
                  comparison.observed_status === null
                    ? copy.shared.unavailable
                    : valueOrFallback(
                        copy.capabilityProbe.statuses[comparison.observed_status],
                        comparison.observed_status,
                      )
                const expected =
                  comparison.live || comparison.expected_status === null
                    ? copy.shared.unavailable
                    : valueOrFallback(
                        copy.capabilityProbe.statuses[comparison.expected_status],
                        comparison.expected_status,
                      )
                const consistency =
                  comparison.live || comparison.is_consistent === null
                    ? copy.shared.unavailable
                    : comparison.is_consistent === true
                    ? copy.capabilityProbe.consistency.yes
                    : copy.capabilityProbe.consistency.no

                return (
                  <tr key={comparison.capability}>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle font-medium text-slate-900 dark:border-slate-800 dark:text-slate-100">
                      <div>{copy.capabilityNames[comparison.capability] ?? comparison.capability}</div>
                      <div className="mt-1 text-xs font-normal text-slate-500 dark:text-slate-400">
                        {copy.capabilityNotes[comparison.capability] ?? copy.shared.unavailable}
                      </div>
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                      {observed}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                      {expected}
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                      {consistency}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
