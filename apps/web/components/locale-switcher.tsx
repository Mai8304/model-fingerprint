"use client"

import { Languages } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useLocale } from "@/lib/i18n/provider"
import type { LocaleKey } from "@/lib/i18n/messages"
import { cn } from "@/lib/utils"

const locales: LocaleKey[] = ["en", "zh-CN", "ja"]

const localeLabelKey: Record<LocaleKey, "locale.english" | "locale.simplifiedChinese" | "locale.japanese"> = {
  en: "locale.english",
  "zh-CN": "locale.simplifiedChinese",
  ja: "locale.japanese",
}

export function LocaleSwitcher({ className }: { className?: string }) {
  const { locale, setLocale, t } = useLocale()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          aria-label={t("actions.changeLanguage")}
          className={cn(className)}
          size="icon"
          type="button"
          variant="outline"
        >
          <Languages className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>{t("actions.language")}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup onValueChange={(value) => setLocale(value as LocaleKey)} value={locale}>
          {locales.map((item) => (
            <DropdownMenuRadioItem key={item} value={item}>
              {t(localeLabelKey[item])}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
