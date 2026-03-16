import { messages, type LocaleKey, type MessageKey } from "@/lib/i18n/messages"

export type MessageValues = Record<string, string | number | undefined>

export type TranslationHelpers = {
  locale: LocaleKey
  t: (key: MessageKey) => string
  format: (key: MessageKey, values?: MessageValues) => string
}

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

export function formatMessage(template: string, values: MessageValues = {}) {
  return template.replaceAll(/\{(\w+)\}/g, (_match, key: string) => {
    const value = values[key]

    return value === undefined ? "" : String(value)
  })
}

export function createTranslationHelpers(locale: LocaleKey): TranslationHelpers {
  const dictionary = getMessages(locale)

  return {
    locale,
    t: (key) => dictionary[key],
    format: (key, values) => formatMessage(dictionary[key], values),
  }
}
