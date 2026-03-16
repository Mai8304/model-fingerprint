"use client"

import { useMemo } from "react"
import { ShieldCheck } from "lucide-react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { createCheckConfigSchema, type CheckConfigValues } from "@/lib/check-config-schema"
import { fingerprintOptions as defaultFingerprintOptions } from "@/lib/fingerprint-options"
import { useLocale } from "@/lib/i18n/provider"
import type { FingerprintOption } from "@/lib/run-types"

type RemoteFieldErrors = Partial<Record<keyof CheckConfigValues, string>>

export function CheckConfigForm({
  disabled,
  fingerprintOptions = defaultFingerprintOptions,
  remoteErrors,
  onSubmit,
}: {
  disabled: boolean
  fingerprintOptions?: FingerprintOption[]
  remoteErrors?: RemoteFieldErrors
  onSubmit: (values: CheckConfigValues) => void | Promise<void>
}) {
  const { t } = useLocale()
  const schema = useMemo(
    () =>
      createCheckConfigSchema((key) => {
        return t(key)
      }),
    [t],
  )
  const form = useForm<CheckConfigValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      apiKey: "",
      baseUrl: "",
      modelName: "",
      fingerprintModel: "",
    },
  })

  const apiKeyError =
    form.formState.errors.apiKey?.message ||
    (form.formState.dirtyFields.apiKey ? undefined : remoteErrors?.apiKey)
  const baseUrlError =
    form.formState.errors.baseUrl?.message ||
    (form.formState.dirtyFields.baseUrl ? undefined : remoteErrors?.baseUrl)
  const modelNameError =
    form.formState.errors.modelName?.message ||
    (form.formState.dirtyFields.modelName ? undefined : remoteErrors?.modelName)
  const fingerprintError =
    form.formState.errors.fingerprintModel?.message ||
    (form.formState.dirtyFields.fingerprintModel
      ? undefined
      : remoteErrors?.fingerprintModel)

  return (
    <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-900 dark:text-slate-100" htmlFor="apiKey">
          {t("form.apiKey")}
        </label>
        <Input
          autoComplete="off"
          id="apiKey"
          placeholder="sk-..."
          type="password"
          {...form.register("apiKey")}
          disabled={disabled}
        />
        {apiKeyError ? (
          <p className="text-sm text-rose-600 dark:text-rose-400">{apiKeyError}</p>
        ) : null}
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-900 dark:text-slate-100" htmlFor="baseUrl">
          {t("form.baseUrl")}
        </label>
        <Input
          id="baseUrl"
          placeholder="https://api.example.com/v1"
          {...form.register("baseUrl")}
          disabled={disabled}
        />
        {baseUrlError ? (
          <p className="text-sm text-rose-600 dark:text-rose-400">{baseUrlError}</p>
        ) : null}
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-900 dark:text-slate-100" htmlFor="modelName">
          {t("form.modelName")}
        </label>
        <Input
          id="modelName"
          placeholder="gpt-4.1-mini"
          {...form.register("modelName")}
          disabled={disabled}
        />
        {modelNameError ? (
          <p className="text-sm text-rose-600 dark:text-rose-400">{modelNameError}</p>
        ) : null}
      </div>

      <div className="space-y-1.5">
        <label
          className="text-sm font-medium text-slate-900 dark:text-slate-100"
          htmlFor="fingerprintModel"
        >
          {t("form.fingerprintModel")}
        </label>
        <select
          className="flex h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-sky-400 focus:bg-white focus:ring-2 focus:ring-sky-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:border-sky-500 dark:focus:bg-slate-950 dark:focus:ring-sky-950"
          id="fingerprintModel"
          {...form.register("fingerprintModel")}
          disabled={disabled || fingerprintOptions.length === 0}
        >
          <option value="">{t("form.selectFingerprintPlaceholder")}</option>
          {fingerprintOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {fingerprintError ? (
          <p className="text-sm text-rose-600 dark:text-rose-400">{fingerprintError}</p>
        ) : null}
      </div>

      <div className="flex items-start gap-3 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-200">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
        <p>{t("form.securityNote")}</p>
      </div>

      <Button className="w-full" disabled={disabled || fingerprintOptions.length === 0} type="submit">
        {t("actions.startCheck")}
      </Button>
    </form>
  )
}
