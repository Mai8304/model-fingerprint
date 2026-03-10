"use client"

import { createContext, useContext, useMemo, useState, type ReactNode } from "react"

import type { LocaleKey, MessageKey } from "@/lib/i18n/messages"
import { getMessages } from "@/lib/i18n/locale"

type LocaleContextValue = {
  locale: LocaleKey
  setLocale: (locale: LocaleKey) => void
  t: (key: MessageKey) => string
}

const LocaleContext = createContext<LocaleContextValue | null>(null)

export function LocaleProvider({
  children,
  initialLocale,
}: {
  children: ReactNode
  initialLocale: LocaleKey
}) {
  const [locale, setLocale] = useState<LocaleKey>(initialLocale)

  const value = useMemo<LocaleContextValue>(() => {
    const dictionary = getMessages(locale)

    return {
      locale,
      setLocale,
      t: (key) => dictionary[key],
    }
  }, [locale])

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale() {
  const context = useContext(LocaleContext)

  if (context === null) {
    throw new Error("useLocale must be used within a LocaleProvider")
  }

  return context
}
