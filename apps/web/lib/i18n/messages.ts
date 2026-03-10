export type LocaleKey = "en" | "zh-CN" | "ja"

export type MessageKey =
  | "app.title"
  | "app.subtitle"
  | "actions.startCheck"
  | "actions.theme"
  | "actions.language"

export const messages: Record<LocaleKey, Record<MessageKey, string>> = {
  en: {
    "app.title": "Model Fingerprint",
    "app.subtitle": "Identify whether a model is what it claims to be through fingerprint comparison.",
    "actions.startCheck": "Start Check",
    "actions.theme": "Theme",
    "actions.language": "Language",
  },
  "zh-CN": {
    "app.title": "模型指纹识别",
    "app.subtitle": "通过模型指纹比对，判断一个模型是否与其声明身份一致。",
    "actions.startCheck": "开始检查",
    "actions.theme": "主题",
    "actions.language": "语言",
  },
  ja: {
    "app.title": "モデル指紋識別",
    "app.subtitle": "モデル指紋比較により、対象モデルが申告どおりのモデルかを判定します。",
    "actions.startCheck": "検査開始",
    "actions.theme": "テーマ",
    "actions.language": "言語",
  },
}
