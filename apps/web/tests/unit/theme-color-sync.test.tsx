import { render } from "@testing-library/react"
import { beforeEach, expect, test, vi } from "vitest"

vi.mock("next-themes", () => ({
  useTheme: vi.fn(),
}))

import { useTheme } from "next-themes"

import { ThemeColorSync, THEME_COLORS } from "@/components/theme-color-sync"

beforeEach(() => {
  document.head.innerHTML = ""
  document.documentElement.style.colorScheme = ""
})

test("syncs the browser theme color for dark mode", () => {
  vi.mocked(useTheme).mockReturnValue({
    resolvedTheme: "dark",
  } as never)

  render(<ThemeColorSync />)

  expect(
    document.querySelector('meta[name="theme-color"]')?.getAttribute("content"),
  ).toBe(THEME_COLORS.dark)
  expect(document.documentElement.style.colorScheme).toBe("dark")
})

test("syncs the browser theme color for light mode", () => {
  vi.mocked(useTheme).mockReturnValue({
    resolvedTheme: "light",
  } as never)

  render(<ThemeColorSync />)

  expect(
    document.querySelector('meta[name="theme-color"]')?.getAttribute("content"),
  ).toBe(THEME_COLORS.light)
  expect(document.documentElement.style.colorScheme).toBe("light")
})
