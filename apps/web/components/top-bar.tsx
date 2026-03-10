"use client"

import { LocaleSwitcher } from "@/components/locale-switcher"
import { ThemeSwitcher } from "@/components/theme-switcher"
import { useLocale } from "@/lib/i18n/provider"

export function TopBar() {
  const { t } = useLocale()

  return (
    <header className="rounded-3xl border border-slate-200 bg-white/90 px-6 py-5 shadow-[0_24px_80px_-48px_rgba(15,23,42,0.5)] backdrop-blur">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
            Research Console
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">{t("app.title")}</h1>
          <p className="max-w-3xl text-sm leading-6 text-slate-600">{t("app.subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
          <LocaleSwitcher />
          <ThemeSwitcher />
        </div>
      </div>
    </header>
  )
}
