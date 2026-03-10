"use client"

import { ShieldCheck } from "lucide-react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { checkConfigSchema, type CheckConfigValues } from "@/lib/check-config-schema"
import { fingerprintOptions } from "@/lib/fingerprint-options"
import { useLocale } from "@/lib/i18n/provider"

export function CheckConfigForm({
  disabled,
  onSubmit,
}: {
  disabled: boolean
  onSubmit: (values: CheckConfigValues) => void
}) {
  const { t } = useLocale()
  const form = useForm<CheckConfigValues>({
    resolver: zodResolver(checkConfigSchema),
    defaultValues: {
      apiKey: "",
      baseUrl: "",
      modelName: "",
      fingerprintModel: "",
    },
  })

  return (
    <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-900" htmlFor="apiKey">
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
        {form.formState.errors.apiKey ? (
          <p className="text-sm text-rose-600">{form.formState.errors.apiKey.message}</p>
        ) : null}
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-900" htmlFor="baseUrl">
          {t("form.baseUrl")}
        </label>
        <Input
          id="baseUrl"
          placeholder="https://api.example.com/v1"
          {...form.register("baseUrl")}
          disabled={disabled}
        />
        {form.formState.errors.baseUrl ? (
          <p className="text-sm text-rose-600">{form.formState.errors.baseUrl.message}</p>
        ) : null}
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-900" htmlFor="modelName">
          {t("form.modelName")}
        </label>
        <Input
          id="modelName"
          placeholder="gpt-4.1-mini"
          {...form.register("modelName")}
          disabled={disabled}
        />
        {form.formState.errors.modelName ? (
          <p className="text-sm text-rose-600">{form.formState.errors.modelName.message}</p>
        ) : null}
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-900" htmlFor="fingerprintModel">
          {t("form.fingerprintModel")}
        </label>
        <select
          className="flex h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-sky-400 focus:bg-white focus:ring-2 focus:ring-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
          id="fingerprintModel"
          {...form.register("fingerprintModel")}
          disabled={disabled}
        >
          <option value="">Select a fingerprint</option>
          {fingerprintOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {form.formState.errors.fingerprintModel ? (
          <p className="text-sm text-rose-600">{form.formState.errors.fingerprintModel.message}</p>
        ) : null}
      </div>

      <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{t("form.securityNote")}</p>
        </div>
      </div>

      <Button className="w-full" disabled={disabled} type="submit">
        {t("actions.startCheck")}
      </Button>
    </form>
  )
}
