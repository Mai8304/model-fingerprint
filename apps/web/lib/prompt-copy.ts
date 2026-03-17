import type { LocaleKey } from "@/lib/i18n/messages"

type PromptDisplayInfo = {
  title: string
  stepLabel?: string | null
  focus?: string | null
}

export const defaultPromptIds = ["p041", "p042", "p043", "p044", "p045"] as const

const promptDisplayInfo: Record<LocaleKey, Record<string, PromptDisplayInfo>> = {
  en: {
    p021: {
      title: "Evidence Judgment",
      stepLabel: "Question 1",
      focus: "Evidence-grounded judgment",
    },
    p022: {
      title: "Context Retrieval",
      stepLabel: "Question 2",
      focus: "Context retrieval and selection",
    },
    p023: {
      title: "Cautious Answering",
      stepLabel: "Question 3",
      focus: "Cautious answering under uncertainty",
    },
    p024: {
      title: "State Tracking",
      stepLabel: "Question 4",
      focus: "State tracking across updates",
    },
    p025: {
      title: "Entity Normalization",
      stepLabel: "Question 5",
      focus: "Entity normalization and alias matching",
    },
    p041: {
      title: "Prompt 1",
      stepLabel: null,
      focus: "Responsibility attribution under complex evidence",
    },
    p042: {
      title: "Prompt 2",
      stepLabel: null,
      focus: "Entity filtering among similar names",
    },
    p043: {
      title: "Prompt 3",
      stepLabel: null,
      focus: "Cautious answering under conflicting evidence",
    },
    p044: {
      title: "Prompt 4",
      stepLabel: null,
      focus: "Final decisions under rule overrides",
    },
    p045: {
      title: "Prompt 5",
      stepLabel: null,
      focus: "Normalization thresholds for aliases and short names",
    },
  },
  "zh-CN": {
    p021: {
      title: "分析模型证据判断能力",
      stepLabel: "第 1 题",
      focus: "证据判断能力",
    },
    p022: {
      title: "分析模型上下文检索能力",
      stepLabel: "第 2 题",
      focus: "上下文检索能力",
    },
    p023: {
      title: "分析模型审慎作答能力",
      stepLabel: "第 3 题",
      focus: "审慎作答能力",
    },
    p024: {
      title: "分析模型状态推演能力",
      stepLabel: "第 4 题",
      focus: "状态推演能力",
    },
    p025: {
      title: "分析模型实体归一能力",
      stepLabel: "第 5 题",
      focus: "实体归一能力",
    },
    p041: {
      title: "Prompt 1",
      stepLabel: null,
      focus: "复杂线索下的责任归因能力",
    },
    p042: {
      title: "Prompt 2",
      stepLabel: null,
      focus: "相近名称的实体筛选能力",
    },
    p043: {
      title: "Prompt 3",
      stepLabel: null,
      focus: "冲突信息下的审慎定答能力",
    },
    p044: {
      title: "Prompt 4",
      stepLabel: null,
      focus: "规则覆盖下的最终判定能力",
    },
    p045: {
      title: "Prompt 5",
      stepLabel: null,
      focus: "别名短名的归一阈值能力",
    },
  },
  ja: {
    p021: {
      title: "根拠判断",
      stepLabel: "問題 1",
      focus: "根拠に基づく判断",
    },
    p022: {
      title: "文脈検索",
      stepLabel: "問題 2",
      focus: "文脈検索と選別",
    },
    p023: {
      title: "慎重回答",
      stepLabel: "問題 3",
      focus: "不確実性下での慎重回答",
    },
    p024: {
      title: "状態推論",
      stepLabel: "問題 4",
      focus: "更新をまたぐ状態推論",
    },
    p025: {
      title: "表記正規化",
      stepLabel: "問題 5",
      focus: "表記ゆれと別名の正規化",
    },
    p041: {
      title: "Prompt 1",
      stepLabel: null,
      focus: "複雑な手がかり下での責任帰属",
    },
    p042: {
      title: "Prompt 2",
      stepLabel: null,
      focus: "類似名称のエンティティ選別",
    },
    p043: {
      title: "Prompt 3",
      stepLabel: null,
      focus: "衝突情報下での慎重回答",
    },
    p044: {
      title: "Prompt 4",
      stepLabel: null,
      focus: "ルール上書き下での最終判定",
    },
    p045: {
      title: "Prompt 5",
      stepLabel: null,
      focus: "別名・短縮名の正規化閾値",
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
    stepLabel: null,
    focus: promptId,
  }
}

export function getPromptTitle(promptId: string, locale: LocaleKey) {
  return getPromptDisplayInfo(promptId, locale).title
}

export function getPromptLabel(promptId: string, locale: LocaleKey) {
  return getPromptTitle(promptId, locale)
}
