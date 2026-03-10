import { messages, type LocaleKey } from "@/lib/i18n/messages"

export function resolveInitialLocale(rawLocale?: string | null): LocaleKey {
  const normalized = (rawLocale ?? "").toLowerCase()

  if (normalized.startsWith("zh-cn") || normalized.startsWith("zh-hans")) {
    return "zh-CN"
  }

  if (normalized.startsWith("ja")) {
    return "ja"
  }

  return "en"
}

export function getMessages(locale: LocaleKey) {
  return messages[locale]
}
