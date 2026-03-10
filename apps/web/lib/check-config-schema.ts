import { z } from "zod"

import { messages, type MessageKey } from "@/lib/i18n/messages"

type ValidationKey =
  | "validation.apiKeyRequired"
  | "validation.baseUrlInvalid"
  | "validation.modelNameRequired"
  | "validation.fingerprintRequired"

export function createCheckConfigSchema(t: (key: ValidationKey) => string) {
  return z.object({
    apiKey: z.string().trim().min(1, t("validation.apiKeyRequired")),
    baseUrl: z.string().trim().url(t("validation.baseUrlInvalid")),
    modelName: z.string().trim().min(1, t("validation.modelNameRequired")),
    fingerprintModel: z.string().trim().min(1, t("validation.fingerprintRequired")),
  })
}

export const checkConfigSchema = createCheckConfigSchema(
  (key) => messages.en[key as MessageKey],
)

export type CheckConfigValues = z.infer<typeof checkConfigSchema>
