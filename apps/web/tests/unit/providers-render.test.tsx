import { render, screen } from "@testing-library/react"

import { Providers } from "@/components/providers"
import { useLocale } from "@/lib/i18n/provider"

function LocaleProbe() {
  const { locale, t } = useLocale()

  return (
    <div>
      <span>{locale}</span>
      <span>{t("app.title")}</span>
    </div>
  )
}

test("renders children with the selected locale messages", () => {
  render(
    <Providers initialLocale="ja">
      <LocaleProbe />
    </Providers>,
  )

  expect(screen.getByText("ja")).toBeInTheDocument()
  expect(screen.getByText("モデル指紋識別")).toBeInTheDocument()
})
