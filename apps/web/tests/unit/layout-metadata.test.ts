import { metadata, viewport } from "@/app/layout"

test("uses the brain emoji favicon", () => {
  expect(metadata.icons).toEqual({
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  })
})

test("declares light and dark browser theme colors", () => {
  expect(viewport.themeColor).toEqual([
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#020617" },
  ])
  expect(viewport.colorScheme).toBe("light dark")
})
