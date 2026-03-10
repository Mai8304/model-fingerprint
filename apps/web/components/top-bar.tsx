"use client"

import Link from "next/link"
import { Fingerprint, Github } from "lucide-react"

import { LocaleSwitcher } from "@/components/locale-switcher"
import { ThemeSwitcher } from "@/components/theme-switcher"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useLocale } from "@/lib/i18n/provider"

export function TopBar() {
  const { t } = useLocale()

  return (
    <header className="rounded-3xl border border-slate-200 bg-white/92 px-4 py-3 shadow-[0_20px_60px_-42px_rgba(15,23,42,0.48)] backdrop-blur dark:border-slate-800 dark:bg-slate-950/88">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 dark:bg-sky-500/12 dark:text-sky-300">
            <Fingerprint className="h-5 w-5" />
          </div>
          <p className="truncate text-sm font-semibold tracking-tight text-slate-950 dark:text-slate-50">
            {t("app.title")}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <LocaleSwitcher />
          <ThemeSwitcher />
          <Link
            aria-label={t("actions.openGithub")}
            className={cn(buttonVariants({ size: "icon", variant: "outline" }))}
            href="https://github.com/Mai8304/model-fingerprint"
            rel="noreferrer"
            target="_blank"
          >
            <Github className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </header>
  )
}
