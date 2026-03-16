import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import { expect, test } from "vitest"

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
const WEB_ROOT = path.resolve(TEST_DIR, "..", "..")

function collectRadixImports(rootDir: string): string[] {
  const imports = new Set<string>()

  function walk(currentDir: string) {
    for (const entry of fs.readdirSync(currentDir, { withFileTypes: true })) {
      const resolved = path.join(currentDir, entry.name)
      if (entry.isDirectory()) {
        walk(resolved)
        continue
      }

      if (!resolved.endsWith(".ts") && !resolved.endsWith(".tsx")) {
        continue
      }

      const source = fs.readFileSync(resolved, "utf-8")
      for (const match of source.matchAll(/from "(@radix-ui\/[^"]+)"/g)) {
        imports.add(match[1])
      }
    }
  }

  walk(rootDir)
  return [...imports].sort()
}

test("declares every Radix UI import in package.json", () => {
  const packageJson = JSON.parse(
    fs.readFileSync(path.join(WEB_ROOT, "package.json"), "utf-8"),
  ) as {
    dependencies?: Record<string, string>
    devDependencies?: Record<string, string>
  }
  const declaredDependencies = new Set<string>([
    ...Object.keys(packageJson.dependencies ?? {}),
    ...Object.keys(packageJson.devDependencies ?? {}),
  ])

  const missingDependencies = collectRadixImports(path.join(WEB_ROOT, "components")).filter(
    (dependency) => !declaredDependencies.has(dependency),
  )

  expect(missingDependencies).toEqual([])
})
