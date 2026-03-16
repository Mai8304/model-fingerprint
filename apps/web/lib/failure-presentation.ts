import type { ErrorCode } from "@/lib/api-contract"
import type { LocaleKey } from "@/lib/i18n/messages"

type UserFacingFailureCode =
  | "AMBIGUOUS_ENDPOINT_PROFILE"
  | "AUTH_FAILED"
  | "ENDPOINT_UNREACHABLE"
  | "MODEL_NOT_FOUND"
  | "PROVIDER_SERVER_ERROR"
  | "RATE_LIMITED"
  | "UNSUPPORTED_ENDPOINT_PROTOCOL"

const userFacingFailureMessages: Record<LocaleKey, Record<UserFacingFailureCode, string>> = {
  en: {
    AMBIGUOUS_ENDPOINT_PROFILE:
      "The configured Base URL could not be matched to a supported endpoint profile. Check whether the Base URL is correct.",
    AUTH_FAILED:
      "Authentication failed for the configured endpoint. Check whether the API key is correct.",
    ENDPOINT_UNREACHABLE:
      "The configured endpoint could not be reached. Check the Base URL, DNS resolution, and network connectivity.",
    MODEL_NOT_FOUND:
      "The configured endpoint could not find the requested model. Check whether the model name is correct.",
    PROVIDER_SERVER_ERROR:
      "The configured endpoint returned a server-side error. Try again later.",
    RATE_LIMITED: "The configured endpoint is currently rate limited. Try again later.",
    UNSUPPORTED_ENDPOINT_PROTOCOL:
      "The configured endpoint did not behave like an OpenAI-compatible Chat Completions API. Check the Base URL and provider protocol.",
  },
  "zh-CN": {
    AMBIGUOUS_ENDPOINT_PROFILE: "当前 Base URL 无法识别为受支持的接口类型，请检查 Base URL 是否正确。",
    AUTH_FAILED: "当前接口鉴权失败，请检查 API Key 是否正确。",
    ENDPOINT_UNREACHABLE: "当前接口无法连接，请检查 Base URL、域名解析和网络可达性。",
    MODEL_NOT_FOUND: "当前接口未找到所填写的模型，请检查模型名称是否正确。",
    PROVIDER_SERVER_ERROR: "当前接口返回了服务端错误，请稍后重试。",
    RATE_LIMITED: "当前接口触发了限流，请稍后重试。",
    UNSUPPORTED_ENDPOINT_PROTOCOL:
      "当前接口没有表现为兼容的 OpenAI Chat Completions API，请检查 Base URL 与供应商协议。",
  },
  ja: {
    AMBIGUOUS_ENDPOINT_PROFILE:
      "設定した Base URL は対応しているエンドポイント種別として認識できません。Base URL を確認してください。",
    AUTH_FAILED:
      "設定したエンドポイントの認証に失敗しました。API Key が正しいか確認してください。",
    ENDPOINT_UNREACHABLE:
      "設定したエンドポイントに接続できません。Base URL、DNS 解決、ネットワーク到達性を確認してください。",
    MODEL_NOT_FOUND:
      "設定したエンドポイントで指定したモデルが見つかりません。モデル名が正しいか確認してください。",
    PROVIDER_SERVER_ERROR:
      "設定したエンドポイントがサーバー側エラーを返しました。しばらく待ってから再試行してください。",
    RATE_LIMITED:
      "設定したエンドポイントでレート制限が発生しています。しばらく待ってから再試行してください。",
    UNSUPPORTED_ENDPOINT_PROTOCOL:
      "設定したエンドポイントは OpenAI 互換の Chat Completions API として動作しませんでした。Base URL とプロバイダ仕様を確認してください。",
  },
}

const opaqueEndpointErrorPatterns = [
  /<urlopen error/i,
  /name or service not known/i,
  /temporary failure in name resolution/i,
  /nodename nor servname provided/i,
  /failed to establish a new connection/i,
  /connection refused/i,
  /connection timed out/i,
  /\btimed out\b/i,
  /\bgetaddrinfo\b/i,
  /no address associated with hostname/i,
]

function looksLikeOpaqueEndpointError(message: string) {
  return opaqueEndpointErrorPatterns.some((pattern) => pattern.test(message))
}

export function humanizeFailureMessage(
  code: ErrorCode | null | undefined,
  message: string | null | undefined,
  locale: LocaleKey,
) {
  if (code !== undefined && code !== null && code in userFacingFailureMessages[locale]) {
    return userFacingFailureMessages[locale][code as UserFacingFailureCode]
  }
  if (message && looksLikeOpaqueEndpointError(message)) {
    return userFacingFailureMessages[locale].ENDPOINT_UNREACHABLE
  }
  return null
}

export function presentFailureMessage({
  code,
  message,
  locale,
  fallback,
}: {
  code: ErrorCode | null | undefined
  message: string | null | undefined
  locale: LocaleKey
  fallback: string
}) {
  return humanizeFailureMessage(code, message, locale) ?? message ?? fallback
}
