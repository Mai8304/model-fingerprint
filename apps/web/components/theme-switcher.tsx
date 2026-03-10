"use client"

import { Monitor, Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

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

type ThemeMode = "light" | "dark" | "system"

const themeModes: ThemeMode[] = ["light", "dark", "system"]

const themeLabelKey: Record<ThemeMode, "theme.light" | "theme.dark" | "theme.system"> = {
  light: "theme.light",
  dark: "theme.dark",
  system: "theme.system",
}

const themeIcon: Record<ThemeMode, typeof Sun> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
}

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme()
  const { t } = useLocale()
  const selectedTheme = (theme as ThemeMode | undefined) ?? "system"
  const TriggerIcon = themeIcon[selectedTheme]

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          aria-label={t("actions.changeTheme")}
          size="icon"
          type="button"
          variant="outline"
        >
          <TriggerIcon className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>{t("actions.theme")}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup
          onValueChange={(value) => setTheme(value as ThemeMode)}
          value={selectedTheme}
        >
          {themeModes.map((item) => (
            <DropdownMenuRadioItem key={item} value={item}>
              {t(themeLabelKey[item])}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
