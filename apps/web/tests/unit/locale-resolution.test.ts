import { resolveInitialLocale } from "@/lib/i18n/locale"

test("falls back to english for unsupported locales", () => {
  expect(resolveInitialLocale("fr-FR")).toBe("en")
})

test("maps simplified chinese locales to zh-CN", () => {
  expect(resolveInitialLocale("zh-CN")).toBe("zh-CN")
  expect(resolveInitialLocale("zh-Hans-CN")).toBe("zh-CN")
})

test("maps japanese locales to ja", () => {
  expect(resolveInitialLocale("ja-JP")).toBe("ja")
})
