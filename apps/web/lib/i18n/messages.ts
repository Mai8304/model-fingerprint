export type LocaleKey = "en" | "zh-CN" | "ja"

export type MessageKey =
  | "app.title"
  | "app.subtitle"
  | "actions.startCheck"
  | "actions.theme"
  | "actions.language"
  | "form.apiKey"
  | "form.baseUrl"
  | "form.modelName"
  | "form.fingerprintModel"
  | "form.securityNote"

export const messages: Record<LocaleKey, Record<MessageKey, string>> = {
  en: {
    "app.title": "Model Fingerprint",
    "app.subtitle": "Identify whether a model is what it claims to be through fingerprint comparison.",
    "actions.startCheck": "Start Check",
    "actions.theme": "Theme",
    "actions.language": "Language",
    "form.apiKey": "API Key",
    "form.baseUrl": "Base URL",
    "form.modelName": "Model Name",
    "form.fingerprintModel": "Fingerprint Model",
    "form.securityNote": "Your API key is used only for this check and is not stored after the request completes.",
  },
  "zh-CN": {
    "app.title": "模型指纹识别",
    "app.subtitle": "通过模型指纹比对，判断一个模型是否与其声明身份一致。",
    "actions.startCheck": "开始检查",
    "actions.theme": "主题",
    "actions.language": "语言",
    "form.apiKey": "API Key",
    "form.baseUrl": "Base URL",
    "form.modelName": "模型名称",
    "form.fingerprintModel": "指纹模型",
    "form.securityNote": "API Key 仅用于本次检测，请求完成后即释放，不会持久化保存。",
  },
  ja: {
    "app.title": "モデル指紋識別",
    "app.subtitle": "モデル指紋比較により、対象モデルが申告どおりのモデルかを判定します。",
    "actions.startCheck": "検査開始",
    "actions.theme": "テーマ",
    "actions.language": "言語",
    "form.apiKey": "API Key",
    "form.baseUrl": "Base URL",
    "form.modelName": "モデル名",
    "form.fingerprintModel": "指紋モデル",
    "form.securityNote": "API Key は今回の検査にのみ使用され、リクエスト完了後に保持されません。",
  },
}
