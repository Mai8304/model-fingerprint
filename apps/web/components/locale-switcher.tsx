"use client"

import { useLocale } from "@/lib/i18n/provider"
import type { LocaleKey } from "@/lib/i18n/messages"

const locales: LocaleKey[] = ["en", "zh-CN", "ja"]

export function LocaleSwitcher() {
  const { locale, setLocale } = useLocale()

  return (
    <div aria-label="Locale switcher">
      {locales.map((item) => (
        <button
          key={item}
          aria-pressed={locale === item}
          onClick={() => setLocale(item)}
          type="button"
        >
          {item}
        </button>
      ))}
    </div>
  )
}
