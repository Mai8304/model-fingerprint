import { readFileSync } from "node:fs"
import { resolve } from "node:path"

test("uses class-based dark mode instead of system media queries", () => {
  const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8")

  expect(css).toContain('@custom-variant dark (&:where(.dark, .dark *));')
})
