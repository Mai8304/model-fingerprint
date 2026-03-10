import type { LocaleKey } from "@/lib/i18n/messages"

const promptLabels: Record<LocaleKey, Record<string, string>> = {
  en: {
    p021: "Prompt 1",
    p022: "Prompt 2",
    p023: "Prompt 3",
    p024: "Prompt 4",
    p025: "Prompt 5",
  },
  "zh-CN": {
    p021: "第 1 题",
    p022: "第 2 题",
    p023: "第 3 题",
    p024: "第 4 题",
    p025: "第 5 题",
  },
  ja: {
    p021: "問題 1",
    p022: "問題 2",
    p023: "問題 3",
    p024: "問題 4",
    p025: "問題 5",
  },
}

export function getPromptLabel(promptId: string, locale: LocaleKey) {
  return promptLabels[locale][promptId] ?? promptId
}
