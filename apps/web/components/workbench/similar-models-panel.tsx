"use client"

import { getWorkbenchCopy } from "@/components/workbench/copy"
import { useLocale } from "@/lib/i18n/provider"
import type { RunSnapshot } from "@/lib/run-types"

function formatScore(value: number | null | undefined, fallback: string) {
  if (value === null || value === undefined) {
    return fallback
  }
  return value.toFixed(3)
}

type SimilarModelRow = {
  rank: number | null
  label: string
  score: number | null
  highlighted: boolean
  selected: boolean
}

function buildRows(run: RunSnapshot): SimilarModelRow[] {
  const result = run.result
  if (
    result === null ||
    result === undefined ||
    (run.resultState !== "formal_result" && run.resultState !== "provisional")
  ) {
    return []
  }

  const ranked = [...(result.candidates ?? [])].sort((left, right) => right.similarity - left.similarity)
  const topFive = ranked.slice(0, 5)
  const selectedFingerprintId = result.selected_fingerprint.id
  const selectedInTopFive = topFive.some((candidate) => candidate.model_id === selectedFingerprintId)
  const selectedCandidate =
    selectedInTopFive
      ? null
      : ranked.find((candidate) => candidate.model_id === selectedFingerprintId) ?? result.selected_candidate

  const rows: SimilarModelRow[] = topFive.map((candidate, index) => ({
    rank: index + 1,
    label: candidate.label,
    score: candidate.similarity,
    highlighted: index === 0,
    selected: candidate.model_id === selectedFingerprintId,
  }))

  if (selectedCandidate !== null && selectedCandidate !== undefined) {
    const selectedRankIndex = ranked.findIndex((candidate) => candidate.model_id === selectedCandidate.model_id)
    rows.push({
      rank: selectedRankIndex >= 0 ? selectedRankIndex + 1 : null,
      label: selectedCandidate.label,
      score: selectedCandidate.similarity,
      highlighted: false,
      selected: true,
    })
  }

  return rows
}

export function SimilarModelsPanel({ run }: { run: RunSnapshot }) {
  const { locale } = useLocale()
  const copy = getWorkbenchCopy(locale)
  const rows = buildRows(run)

  return (
    <section className="min-w-0 rounded-2xl border border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900/70">
      <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
        {copy.similarModels.title}
      </h3>

      {rows.length === 0 ? (
        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
          {copy.similarModels.empty}
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[520px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  {copy.similarModels.columns.rank}
                </th>
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  {copy.similarModels.columns.model}
                </th>
                <th className="border-b border-slate-200 px-3 py-2 dark:border-slate-800">
                  {copy.similarModels.columns.score}
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={`${row.rank ?? "selected"}:${row.label}`}
                  className={
                    row.highlighted
                      ? "bg-sky-50/70 dark:bg-sky-950/20"
                      : row.selected
                        ? "bg-slate-50 dark:bg-slate-900/40"
                        : undefined
                  }
                >
                  <td className="border-b border-slate-100 px-3 py-3 align-middle font-medium text-slate-900 dark:border-slate-800 dark:text-slate-100">
                    {row.rank ?? copy.shared.unavailable}
                  </td>
                  <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-900 dark:border-slate-800 dark:text-slate-100">
                    <div className={row.highlighted ? "font-semibold" : "font-medium"}>{row.label}</div>
                    {row.selected && row.rank !== 1 ? (
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {copy.similarModels.selectedFingerprint}
                      </div>
                    ) : null}
                  </td>
                  <td className="border-b border-slate-100 px-3 py-3 align-middle text-slate-700 dark:border-slate-800 dark:text-slate-300">
                    {formatScore(row.score, copy.shared.unavailable)}
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
