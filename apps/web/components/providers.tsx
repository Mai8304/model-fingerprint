"use client"

import type { ReactNode } from "react"
import { ThemeProvider } from "next-themes"

import { LocaleProvider } from "@/lib/i18n/provider"
import type { LocaleKey } from "@/lib/i18n/messages"

export function Providers({
  children,
  initialLocale = "en",
}: {
  children: ReactNode
  initialLocale?: LocaleKey
}) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <LocaleProvider initialLocale={initialLocale}>{children}</LocaleProvider>
    </ThemeProvider>
  )
}
