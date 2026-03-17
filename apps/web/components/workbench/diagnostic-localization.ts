"use client"

import { formatWorkbench, getWorkbenchCopy } from "@/components/workbench/copy"
import type { LocaleKey } from "@/lib/i18n/messages"
import { getPromptTitle } from "@/lib/prompt-copy"

const exactMessages: Record<LocaleKey, Record<string, string>> = {
  en: {
    "reasoning coverage is below the profile expectation":
      "Reasoning coverage is below the fingerprint profile expectation.",
    "run contains unsupported capability prompts":
      "The run contains prompts that require unsupported capabilities.",
    "answer coverage is zero": "Answer coverage is zero.",
    "Review the prompt diagnostics table for per-prompt transport and parsing details.":
      "Review the prompt diagnostics table for per-prompt transport and parsing details.",
    "Resolve the blocking prompt failures and rerun to reach at least 3 scoreable prompts.":
      "Resolve the blocking prompt failures and rerun to reach at least 3 scoreable prompts.",
    "Verify provider latency, endpoint reachability, and rate limits before rerunning.":
      "Verify provider latency, endpoint reachability, and rate limits before rerunning.",
    "Verify the endpoint can return stable structured JSON for the current fingerprint prompt suite.":
      "Verify the endpoint can return stable structured JSON for the current fingerprint prompt suite.",
  },
  "zh-CN": {
    "reasoning coverage is below the profile expectation": "推理覆盖度低于指纹画像的预期值。",
    "run contains unsupported capability prompts": "检测结果包含不受支持的能力题目。",
    "answer coverage is zero": "答案覆盖度为 0。",
    "Review the prompt diagnostics table for per-prompt transport and parsing details.":
      "请查看 Prompt 探测表中的逐题传输与解析详情。",
    "Resolve the blocking prompt failures and rerun to reach at least 3 scoreable prompts.":
      "请先解决阻塞的 Prompt 失败问题，再重新检测，至少拿到 3 道可计分题。",
    "Verify provider latency, endpoint reachability, and rate limits before rerunning.":
      "重新检测前，请检查供应商延迟、接口可达性和限流状态。",
    "Verify the endpoint can return stable structured JSON for the current fingerprint prompt suite.":
      "请确认该接口能为当前指纹 Prompt 套件稳定返回结构化 JSON。",
  },
  ja: {
    "reasoning coverage is below the profile expectation":
      "推論カバレッジが指紋プロファイルの想定値を下回っています。",
    "run contains unsupported capability prompts":
      "未対応の能力を要求する Prompt が含まれています。",
    "answer coverage is zero": "回答カバレッジが 0 です。",
    "Review the prompt diagnostics table for per-prompt transport and parsing details.":
      "Prompt プローブ表で各問題の転送と解析の詳細を確認してください。",
    "Resolve the blocking prompt failures and rerun to reach at least 3 scoreable prompts.":
      "阻害している Prompt の失敗を解消し、採点可能な問題が 3 問以上になるよう再実行してください。",
    "Verify provider latency, endpoint reachability, and rate limits before rerunning.":
      "再実行前に、プロバイダ遅延、エンドポイント到達性、レート制限を確認してください。",
    "Verify the endpoint can return stable structured JSON for the current fingerprint prompt suite.":
      "エンドポイントが現在の指紋 Prompt スイートに対して安定した構造化 JSON を返せることを確認してください。",
  },
}

function localizePromptStatusToken(
  token: string,
  locale: LocaleKey,
  copy: ReturnType<typeof getWorkbenchCopy>,
) {
  return copy.promptProbe.statuses[token] ?? exactMessages[locale][token] ?? token
}

export function localizeDiagnosticText(
  text: string,
  locale: LocaleKey,
  copy: ReturnType<typeof getWorkbenchCopy>,
) {
  const exact = exactMessages[locale][text]
  if (exact !== undefined) {
    return exact
  }

  const nearestCandidate = text.match(
    /^The selected fingerprint is not the closest candidate\. Inspect (.+) as the nearest match\.$/,
  )
  if (nearestCandidate) {
    const [, candidate] = nearestCandidate
    if (locale === "zh-CN") {
      return `所选指纹不是最接近候选，请重点检查 ${candidate}。`
    }
    if (locale === "ja") {
      return `選択した指紋は最有力候補ではありません。${candidate} を最も近い候補として確認してください。`
    }
    return text
  }

  const protocolStatusMatch = text.match(/^protocol_status=([a-z_]+)$/)
  if (protocolStatusMatch) {
    const [, status] = protocolStatusMatch
    if (locale === "zh-CN") {
      return `协议状态为 ${copy.protocolStatuses[status] ?? status}。`
    }
    if (locale === "ja") {
      return `プロトコル状態は ${copy.protocolStatuses[status] ?? status} です。`
    }
    return `Protocol status is ${copy.protocolStatuses[status] ?? status}.`
  }

  const answerThresholdMatch = text.match(/^answer coverage below threshold \((.+)\)$/)
  if (answerThresholdMatch) {
    const [, detail] = answerThresholdMatch
    if (locale === "zh-CN") {
      return `答案覆盖度低于阈值（${detail}）。`
    }
    if (locale === "ja") {
      return `回答カバレッジが閾値を下回っています（${detail}）。`
    }
    return `Answer coverage is below the threshold (${detail}).`
  }

  const reasoningThresholdMatch = text.match(/^reasoning coverage below threshold \((.+)\)$/)
  if (reasoningThresholdMatch) {
    const [, detail] = reasoningThresholdMatch
    if (locale === "zh-CN") {
      return `推理覆盖度低于阈值（${detail}）。`
    }
    if (locale === "ja") {
      return `推論カバレッジが閾値を下回っています（${detail}）。`
    }
    return `Reasoning coverage is below the threshold (${detail}).`
  }

  const promptIssueMatch = text.match(/^(p\d+):\s*(.+)$/)
  if (promptIssueMatch) {
    const [, promptId, detail] = promptIssueMatch
    const promptTitle = getPromptTitle(promptId, locale)
    const localizedDetail = localizePromptStatusToken(detail, locale, copy)
    if (locale === "zh-CN") {
      return `${promptTitle}：${localizedDetail}。`
    }
    if (locale === "ja") {
      return `${promptTitle}：${localizedDetail}。`
    }
    return `${promptTitle}: ${localizedDetail}.`
  }

  return text
}

export function formatPromptReason({
  promptId,
  similarity,
  locale,
  copy,
}: {
  promptId: string
  similarity: string
  locale: LocaleKey
  copy: ReturnType<typeof getWorkbenchCopy>
}) {
  return formatWorkbench(copy.conclusion.patterns.promptSimilarity, {
    prompt: getPromptTitle(promptId, locale),
    similarity,
  })
}

export function formatPromptNotScoreableReason({
  promptId,
  detail,
  locale,
  copy,
}: {
  promptId: string
  detail: string | null | undefined
  locale: LocaleKey
  copy: ReturnType<typeof getWorkbenchCopy>
}) {
  const localizedDetail =
    detail === null || detail === undefined || detail === ""
      ? ""
      : locale === "en"
        ? ` (${localizeDiagnosticText(detail, locale, copy)})`
        : `（${localizeDiagnosticText(detail, locale, copy)}）`

  return formatWorkbench(copy.conclusion.patterns.promptNotScoreable, {
    prompt: getPromptTitle(promptId, locale),
    detail: localizedDetail,
  })
}
