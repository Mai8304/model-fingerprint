import type { LocaleKey } from "@/lib/i18n/messages"

type PromptDisplayInfo = {
  title: string
  stepLabel: string
}

export const defaultPromptIds = ["p021", "p022", "p023", "p024", "p025"] as const

const promptDisplayInfo: Record<LocaleKey, Record<string, PromptDisplayInfo>> = {
  en: {
    p021: {
      title: "Evidence Judgment",
      stepLabel: "Question 1",
    },
    p022: {
      title: "Context Retrieval",
      stepLabel: "Question 2",
    },
    p023: {
      title: "Cautious Answering",
      stepLabel: "Question 3",
    },
    p024: {
      title: "State Tracking",
      stepLabel: "Question 4",
    },
    p025: {
      title: "Entity Normalization",
      stepLabel: "Question 5",
    },
  },
  "zh-CN": {
    p021: {
      title: "分析模型证据判断能力",
      stepLabel: "第 1 题",
    },
    p022: {
      title: "分析模型上下文检索能力",
      stepLabel: "第 2 题",
    },
    p023: {
      title: "分析模型审慎作答能力",
      stepLabel: "第 3 题",
    },
    p024: {
      title: "分析模型状态推演能力",
      stepLabel: "第 4 题",
    },
    p025: {
      title: "分析模型实体归一能力",
      stepLabel: "第 5 题",
    },
  },
  ja: {
    p021: {
      title: "根拠判断",
      stepLabel: "問題 1",
    },
    p022: {
      title: "文脈検索",
      stepLabel: "問題 2",
    },
    p023: {
      title: "慎重回答",
      stepLabel: "問題 3",
    },
    p024: {
      title: "状態推論",
      stepLabel: "問題 4",
    },
    p025: {
      title: "表記正規化",
      stepLabel: "問題 5",
    },
  },
}

export function getPromptDisplayInfo(promptId: string, locale: LocaleKey): PromptDisplayInfo {
  const localized = promptDisplayInfo[locale][promptId]
  if (localized !== undefined) {
    return localized
  }
  return {
    title: promptId,
    stepLabel: promptId,
  }
}

export function getPromptTitle(promptId: string, locale: LocaleKey) {
  return getPromptDisplayInfo(promptId, locale).title
}

export function getPromptLabel(promptId: string, locale: LocaleKey) {
  return getPromptTitle(promptId, locale)
}
