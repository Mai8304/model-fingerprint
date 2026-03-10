"use client"

import { useTheme } from "next-themes"

export function ThemeSwitcher() {
  const { resolvedTheme, setTheme } = useTheme()

  return (
    <div aria-label="Theme switcher">
      {(["light", "dark", "system"] as const).map((theme) => (
        <button
          key={theme}
          aria-pressed={resolvedTheme === theme}
          onClick={() => setTheme(theme)}
          type="button"
        >
          {theme}
        </button>
      ))}
    </div>
  )
}
