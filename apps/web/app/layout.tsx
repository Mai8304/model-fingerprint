import type { Metadata } from "next"
import type { ReactNode } from "react"
import { headers } from "next/headers"

import { Providers } from "@/components/providers"
import { resolveInitialLocale } from "@/lib/i18n/locale"

import "./globals.css"

export const metadata: Metadata = {
  title: "Model Fingerprint",
  description: "Model identity verification through fingerprint comparison."
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  const requestHeaders = await headers()
  const initialLocale = resolveInitialLocale(requestHeaders.get("accept-language"))

  return (
    <html lang={initialLocale} suppressHydrationWarning>
      <body>
        <Providers initialLocale={initialLocale}>{children}</Providers>
      </body>
    </html>
  )
}
