"use client"

import { getWorkbenchCopy } from "@/components/workbench/copy"
import { useLocale } from "@/lib/i18n/provider"
import type {
  FingerprintCapabilitySummary,
  FingerprintRegistryItem,
} from "@/lib/run-types"

function formatConfidence(confidence: number | null | undefined) {
  if (confidence === null || confidence === undefined) {
    return null
  }
  return `${Math.round(confidence * 100)}%`
}

function CapabilityCell({
  summary,
  statusCopy,
  fallback,
}: {
  summary: FingerprintCapabilitySummary | null | undefined
  statusCopy: Record<string, string>
  fallback: string
}) {
  if (
    summary === null ||
    summary === undefined ||
    summary.status === null ||
    summary.status === undefined
  ) {
    return <span>{fallback}</span>
  }

  const confidence = formatConfidence(summary.confidence)

  return (
    <div>
      <div>{statusCopy[summary.status] ?? summary.status}</div>
      {confidence === null ? null : (
        <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{confidence}</div>
      )}
    </div>
  )
}

export function FingerprintCapabilityMatrix({
  items,
}: {
  items: FingerprintRegistryItem[]
}) {
  const { locale } = useLocale()
  const copy = getWorkbenchCopy(locale)

  return (
    <section className="min-w-0 rounded-2xl border border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900/70">
      <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
        {copy.fingerprintMatrix.title}
      </h3>

      {items.length === 0 ? (
        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
          {copy.fingerprintMatrix.empty}
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  {copy.fingerprintMatrix.columns.model}
                </th>
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  <div>{copy.fingerprintMatrix.columns.image}</div>
                  <div className="mt-1 text-[11px] font-normal normal-case tracking-normal text-slate-500 dark:text-slate-400">
                    {copy.capabilityNotes.image_generation}
                  </div>
                </th>
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  <div>{copy.fingerprintMatrix.columns.vision}</div>
                  <div className="mt-1 text-[11px] font-normal normal-case tracking-normal text-slate-500 dark:text-slate-400">
                    {copy.capabilityNotes.vision_understanding}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td className="border-b border-slate-100 px-3 py-3 align-middle font-medium text-slate-900 dark:border-slate-800 dark:text-slate-100">
                    {item.label}
                  </td>
                  <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                    <CapabilityCell
                      summary={item.image_generation}
                      statusCopy={copy.capabilityProbe.statuses}
                      fallback={copy.shared.unavailable}
                    />
                  </td>
                  <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                    <CapabilityCell
                      summary={item.vision_understanding}
                      statusCopy={copy.capabilityProbe.statuses}
                      fallback={copy.shared.unavailable}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
