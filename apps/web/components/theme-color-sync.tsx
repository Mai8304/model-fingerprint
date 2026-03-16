"use client"

import { useEffect } from "react"
import { useTheme } from "next-themes"

export const THEME_COLORS = {
  light: "#ffffff",
  dark: "#020617",
} as const

function upsertThemeColorMeta(color: string) {
  let meta = document.querySelector('meta[name="theme-color"]')
  if (!(meta instanceof HTMLMetaElement)) {
    meta = document.createElement("meta")
    meta.setAttribute("name", "theme-color")
    document.head.appendChild(meta)
  }
  meta.setAttribute("content", color)
}

export function ThemeColorSync() {
  const { resolvedTheme } = useTheme()

  useEffect(() => {
    const activeTheme = resolvedTheme === "dark" ? "dark" : "light"
    document.documentElement.style.colorScheme = activeTheme
    upsertThemeColorMeta(THEME_COLORS[activeTheme])
  }, [resolvedTheme])

  return null
}
