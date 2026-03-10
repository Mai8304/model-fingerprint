import { z } from "zod"

export const checkConfigSchema = z.object({
  apiKey: z.string().trim().min(1, "API key is required."),
  baseUrl: z.string().trim().url("Base URL must be a valid URL."),
  modelName: z.string().trim().min(1, "Model name is required."),
  fingerprintModel: z.string().trim().min(1, "Choose a fingerprint model."),
})

export type CheckConfigValues = z.infer<typeof checkConfigSchema>
