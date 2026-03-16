import type { Metadata, Viewport } from "next"
import type { ReactNode } from "react"
import { headers } from "next/headers"

import { Providers } from "@/components/providers"
import { resolveInitialLocale } from "@/lib/i18n/locale"

import "./globals.css"

export const metadata: Metadata = {
  title: "Model Fingerprint",
  description: "Model identity verification through fingerprint comparison.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
}

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#020617" },
  ],
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
