import { checkConfigSchema } from "@/lib/check-config-schema"

test("requires api key, base url, model name, and fingerprint model", () => {
  const result = checkConfigSchema.safeParse({})

  expect(result.success).toBe(false)
})

test("rejects invalid base urls", () => {
  const result = checkConfigSchema.safeParse({
    apiKey: "sk-test",
    baseUrl: "not-a-url",
    modelName: "gpt-4.1-mini",
    fingerprintModel: "gpt-4.1-mini",
  })

  expect(result.success).toBe(false)
})
