"use client"

import type { LocaleKey } from "@/lib/i18n/messages"

type WorkbenchCopy = {
  conclusion: {
    sectionTitle: string
    placeholder: string
    whyTitle: string
    evidenceTitle: string
    reasons: {
      range: string
      capabilities: string
      prompts: string
      strength: string
      none: string
    }
    patterns: {
      rangeInside: string
      rangeDeviation: string
      capabilityLine: string
      capabilityConsistent: string
      capabilityMismatch: string
      capabilityInsufficient: string
      promptNotScoreable: string
      promptSimilarity: string
      promptAllClose: string
      metricValue: string
      coverageValue: string
    }
    labels: {
      running: string
      configurationError: string
      stopped: string
      insufficientEvidence: string
      incompatibleProtocol: string
      provisional: string
      highlyConsistent: string
      similar: string
      mismatch: string
      unknown: string
    }
    messages: {
      running: string
      configurationError: string
      stopped: string
      insufficientEvidence: string
      incompatibleProtocol: string
      provisional: string
      highlyConsistent: string
      similar: string
      mismatch: string
      unknown: string
    }
    firstSentence: {
      highlyConsistent: string
      similar: string
      mismatch: string
      unknown: string
      provisional: string
    }
  }
  capabilityProbe: {
    title: string
    empty: string
    columns: {
      capability: string
      observed: string
      expected: string
      consistent: string
    }
    statuses: Record<string, string>
    consistency: {
      yes: string
      no: string
      unknown: string
    }
  }
  promptProbe: {
    title: string
    empty: string
    columns: {
      prompt: string
      status: string
      similarity: string
      scoreable: string
      error: string
      summary: string
    }
    statuses: Record<string, string>
    summaries: {
      waiting: string
      running: string
      runningWithElapsed: string
      completed: string
      completedWithElapsed: string
      failed: string
      stopped: string
    }
  }
  diagnostics: {
    title: string
    empty: string
    metrics: {
      similarity: string
      fingerprintRange: string
      rangeGap: string
      topCandidate: string
      margin: string
      consistency: string
      scoreablePrompts: string
      answerCoverage: string
      reasoningCoverage: string
      protocolStatus: string
    }
    sections: {
      protocolIssues: string
      hardMismatches: string
      blockingReasons: string
      recommendations: string
    }
    none: string
  }
  similarModels: {
    title: string
    empty: string
    columns: {
      rank: string
      model: string
      score: string
    }
    selectedFingerprint: string
  }
  fingerprintMatrix: {
    title: string
    empty: string
    columns: {
      model: string
      image: string
      vision: string
    }
  }
  shared: {
    yes: string
    no: string
    unavailable: string
  }
  capabilityNames: Record<string, string>
  capabilityNotes: Record<string, string>
  protocolStatuses: Record<string, string>
  range: {
    inside: string
    below: string
    above: string
    unavailable: string
  }
}

const workbenchCopy: Record<LocaleKey, WorkbenchCopy> = {
  en: {
    conclusion: {
      sectionTitle: "Formal Conclusion",
      placeholder:
        "Once a check starts, this panel shows the conclusion first, then the capability, prompt, and detailed diagnostic evidence.",
      whyTitle: "Why This Conclusion",
      evidenceTitle: "Key Evidence",
      reasons: {
        range: "Fingerprint range gap",
        capabilities: "Capability differences",
        prompts: "Prompt-level differences",
        strength: "Evidence strength",
        none: "No additional issues were found for this conclusion.",
      },
      patterns: {
        rangeInside: "The result stays inside the fingerprint range {range}.",
        rangeDeviation: "{gap}; fingerprint range {range}.",
        capabilityLine: "{capability}: {observed} / {expected} / {consistency}.",
        capabilityConsistent: "{capability}: {consistency} ({status})",
        capabilityMismatch:
          "{capability}: {consistency} (tested model: {observed}; fingerprint expectation: {expected})",
        capabilityInsufficient: "{capability}: {consistency}",
        promptNotScoreable: "{prompt}: not scoreable{detail}.",
        promptSimilarity: "{prompt}: similarity {similarity}.",
        promptAllClose: "All scoreable prompts stayed close to the selected fingerprint.",
        metricValue: "{label} {value}.",
        coverageValue: "{answerLabel} {answer} / {reasoningLabel} {reasoning}.",
      },
      labels: {
        running: "Conclusion In Progress",
        configurationError: "Configuration Error",
        stopped: "Check Stopped",
        insufficientEvidence: "Insufficient Evidence",
        incompatibleProtocol: "Incompatible Protocol",
        provisional: "Provisional Conclusion",
        highlyConsistent: "Highly Consistent",
        similar: "Similar",
        mismatch: "Mismatch",
        unknown: "Unknown",
      },
      messages: {
        running: "The system is still collecting evidence from the configured endpoint.",
        configurationError: "The endpoint configuration did not pass validation, so no trustworthy comparison is available.",
        stopped: "The run stopped before enough evidence was collected for a reliable comparison.",
        insufficientEvidence: "The run completed without enough scoreable evidence to support a formal attribution result.",
        incompatibleProtocol: "The endpoint response protocol was unstable, so the fingerprint comparison is not trustworthy.",
        provisional: "The run is incomplete. Treat the current ranking as a temporary observation rather than a final result.",
        highlyConsistent:
          "The tested model is highly consistent with the selected fingerprint based on the available evidence.",
        similar:
          "The tested model is currently closest to the selected fingerprint, but the evidence is not strong enough for a highly consistent conclusion.",
        mismatch:
          "The tested model does not match the selected fingerprint and is better explained by another candidate.",
        unknown:
          "The comparison completed, but the available signal is still too weak for a reliable attribution.",
      },
      firstSentence: {
        highlyConsistent:
          "The tested model is highly consistent with the selected fingerprint model {model}.",
        similar:
          "The tested model is similar to the selected fingerprint, but the evidence is not strong enough for a highly consistent conclusion.",
        mismatch: "The tested model does not match the selected fingerprint.",
        unknown:
          "The system cannot determine whether the tested model belongs to the selected fingerprint.",
        provisional:
          "The run is not complete yet. Treat the current ranking as a temporary observation rather than a final result.",
      },
    },
    capabilityProbe: {
      title: "Capability Probe",
      empty: "Capability comparison data is not available yet.",
      columns: {
        capability: "Capability",
        observed: "Observed",
        expected: "Expected",
        consistent: "Consistent",
      },
      statuses: {
        pending: "Pending",
        running: "Running",
        supported: "Supported",
        accepted_but_ignored: "Request accepted, but capability did not take effect",
        unsupported: "Unsupported",
        insufficient_evidence: "Insufficient evidence",
      },
      consistency: {
        yes: "Consistent",
        no: "Not consistent",
        unknown: "Insufficient evidence",
      },
    },
    promptProbe: {
      title: "Prompt Probe",
      empty: "Prompt comparison data is not available yet.",
      columns: {
        prompt: "Prompt",
        status: "Status",
        similarity: "Similarity",
        scoreable: "Scoreable",
        error: "Error",
        summary: "Evaluation Focus",
      },
      statuses: {
        pending: "Pending",
        running: "Running",
        completed: "Completed",
        failed: "Failed",
        stopped: "Stopped",
        timeout: "Timeout",
        transport_error: "Transport error",
        unsupported_capability: "Unsupported capability",
        truncated: "Truncated",
        invalid_response: "Invalid response",
        canonicalization_error: "Canonicalization error",
      },
      summaries: {
        waiting: "Waiting to start",
        running: "Collecting response",
        runningWithElapsed: "Collecting response · {elapsed}",
        completed: "Completed",
        completedWithElapsed: "Completed · {elapsed}",
        failed: "Execution failed",
        stopped: "Stopped before completion",
      },
    },
    diagnostics: {
      title: "Detailed Diagnostics",
      empty: "Detailed diagnostics will appear after evidence is available.",
      metrics: {
        similarity: "Observed Similarity",
        fingerprintRange: "Fingerprint Range",
        rangeGap: "Range Gap",
        topCandidate: "Nearest Candidate",
        margin: "Margin",
        consistency: "Consistency",
        scoreablePrompts: "Scoreable Prompts",
        answerCoverage: "Answer Coverage",
        reasoningCoverage: "Reasoning Coverage",
        protocolStatus: "Protocol Status",
      },
      sections: {
        protocolIssues: "Protocol Issues",
        hardMismatches: "Hard Mismatches",
        blockingReasons: "Blocking Reasons",
        recommendations: "Recommendations",
      },
      none: "None",
    },
    similarModels: {
      title: "Similar Models (Top 5)",
      empty: "The closest model ranking will appear after comparison data is available.",
      columns: {
        rank: "Rank",
        model: "Model",
        score: "Score",
      },
      selectedFingerprint: "Selected fingerprint",
    },
    fingerprintMatrix: {
      title: "Fingerprint Capability Matrix",
      empty: "Fingerprint capability summaries are not available yet.",
      columns: {
        model: "Model",
        image: "Image",
        vision: "Vision",
      },
    },
    shared: {
      yes: "Yes",
      no: "No",
      unavailable: "-",
    },
    capabilityNames: {
      thinking: "Thinking",
      tools: "Tools",
      streaming: "Streaming",
      image_generation: "Image",
      vision_understanding: "Vision",
    },
    capabilityNotes: {
      thinking: "Chain of thought",
      tools: "Tool calls",
      streaming: "Streaming",
      image_generation: "Image generation",
      vision_understanding: "Visual understanding",
    },
    protocolStatuses: {
      compatible: "Compatible",
      insufficient_evidence: "Insufficient evidence",
      incompatible_protocol: "Incompatible protocol",
    },
    range: {
      inside: "Within the fingerprint range",
      below: "{delta} below the lower bound",
      above: "{delta} above the upper bound",
      unavailable: "Range unavailable",
    },
  },
  "zh-CN": {
    conclusion: {
      sectionTitle: "正式结论",
      placeholder: "检测开始后，这里会先给出正式结论，再展开能力、Prompt 与详细诊断证据。",
      whyTitle: "为什么得出这个结论",
      evidenceTitle: "关键证据",
      reasons: {
        range: "指纹区间偏差",
        capabilities: "能力项差异",
        prompts: "Prompt 级差异",
        strength: "证据强度问题",
        none: "当前没有发现额外的异常原因。",
      },
      patterns: {
        rangeInside: "结果位于指纹区间 {range} 内。",
        rangeDeviation: "{gap}；指纹置信区间 {range}。",
        capabilityLine: "{capability}：测试模型为 {observed}，指纹期望为 {expected}，判断为 {consistency}。",
        capabilityConsistent: "{capability}：{consistency}（{status}）",
        capabilityMismatch: "{capability}：{consistency}（测试模型：{observed}；指纹期望：{expected}）",
        capabilityInsufficient: "{capability}：{consistency}",
        promptNotScoreable: "{prompt}：不可计分{detail}。",
        promptSimilarity: "{prompt}：相似度 {similarity}。",
        promptAllClose: "所有可计分 Prompt 都与所选指纹保持接近。",
        metricValue: "{label}{value}。",
        coverageValue: "{answerLabel}{answer} / {reasoningLabel}{reasoning}。",
      },
      labels: {
        running: "结论生成中",
        configurationError: "配置错误",
        stopped: "检测已停止",
        insufficientEvidence: "证据不足",
        incompatibleProtocol: "协议异常",
        provisional: "临时结论",
        highlyConsistent: "高度一致",
        similar: "相似",
        mismatch: "不一致",
        unknown: "未知",
      },
      messages: {
        running: "系统正在从当前配置的接口收集证据。",
        configurationError: "当前接口配置未通过校验，因此无法生成可信的比对结果。",
        stopped: "检测在收集到足够证据之前被停止。",
        insufficientEvidence: "本轮检测缺少足够的可计分证据，无法支持正式归因结论。",
        incompatibleProtocol: "接口响应协议不稳定，因此当前指纹比对结果不可信。",
        provisional: "检测尚未完整完成，请将当前排序仅视为临时观察，不作为最终结论。",
        highlyConsistent: "根据当前证据，测试模型与所选指纹模型高度一致。",
        similar: "测试模型目前最接近所选指纹模型，但证据强度还不足以支持“高度一致”。",
        mismatch: "测试模型与所选指纹模型不一致，更可能属于其他候选模型。",
        unknown: "检测已经完成，但当前信号仍不足以形成可靠归因。",
      },
      firstSentence: {
        highlyConsistent: "测试模型与所选指纹模型 {model} 高度一致。",
        similar: "测试模型与所选指纹模型相似，但证据强度不足以支持“高度一致”。",
        mismatch: "测试模型与所选指纹模型不一致，更可能属于其他候选模型。",
        unknown: "当前无法可靠判断测试模型是否属于所选指纹模型。",
        provisional: "当前检测尚未完成，请将当前排序仅视为临时观察，不作为最终结论。",
      },
    },
    capabilityProbe: {
      title: "能力探测",
      empty: "当前还没有能力对比数据。",
      columns: {
        capability: "能力项",
        observed: "测试模型状态",
        expected: "指纹期望状态",
        consistent: "是否一致",
      },
      statuses: {
        pending: "待开始",
        running: "检测中",
        supported: "支持",
        accepted_but_ignored: "请求已接受，但能力未生效",
        unsupported: "不支持",
        insufficient_evidence: "证据不足",
      },
      consistency: {
        yes: "一致",
        no: "不一致",
        unknown: "证据不足",
      },
    },
    promptProbe: {
      title: "Prompt 探测",
      empty: "当前还没有 Prompt 对比数据。",
      columns: {
        prompt: "Prompt",
        status: "状态",
        similarity: "相似度",
        scoreable: "是否可计分",
        error: "错误/异常",
        summary: "测评重点",
      },
      statuses: {
        pending: "待开始",
        running: "进行中",
        completed: "已完成",
        failed: "失败",
        stopped: "已停止",
        timeout: "超时",
        transport_error: "传输错误",
        unsupported_capability: "能力不支持",
        truncated: "响应截断",
        invalid_response: "响应无效",
        canonicalization_error: "规范化失败",
      },
      summaries: {
        waiting: "等待开始",
        running: "正在收集响应",
        runningWithElapsed: "正在收集响应 · {elapsed}",
        completed: "已完成",
        completedWithElapsed: "已完成 · {elapsed}",
        failed: "执行失败",
        stopped: "已停止",
      },
    },
    diagnostics: {
      title: "详细诊断信息",
      empty: "检测完成后，这里会展示详细诊断证据。",
      metrics: {
        similarity: "观测相似度",
        fingerprintRange: "指纹置信区间",
        rangeGap: "区间差值",
        topCandidate: "最接近候选",
        margin: "领先差值",
        consistency: "一致性",
        scoreablePrompts: "可计分题数",
        answerCoverage: "答案覆盖度",
        reasoningCoverage: "推理覆盖度",
        protocolStatus: "协议状态",
      },
      sections: {
        protocolIssues: "协议问题",
        hardMismatches: "硬性不匹配",
        blockingReasons: "阻塞原因",
        recommendations: "建议操作",
      },
      none: "无",
    },
    similarModels: {
      title: "相似模型列表（Top 5）",
      empty: "比对完成后，这里会展示最接近的模型排序。",
      columns: {
        rank: "排名",
        model: "模型",
        score: "得分",
      },
      selectedFingerprint: "所选指纹模型",
    },
    fingerprintMatrix: {
      title: "指纹模型能力矩阵",
      empty: "暂时还没有可展示的指纹能力摘要。",
      columns: {
        model: "模型",
        image: "Image",
        vision: "Vision",
      },
    },
    shared: {
      yes: "是",
      no: "否",
      unavailable: "-",
    },
    capabilityNames: {
      thinking: "Thinking",
      tools: "Tools",
      streaming: "Streaming",
      image_generation: "Image",
      vision_understanding: "Vision",
    },
    capabilityNotes: {
      thinking: "思考链",
      tools: "工具调用",
      streaming: "流式输出",
      image_generation: "文生图",
      vision_understanding: "看图理解",
    },
    protocolStatuses: {
      compatible: "兼容",
      insufficient_evidence: "证据不足",
      incompatible_protocol: "协议异常",
    },
    range: {
      inside: "位于指纹区间内",
      below: "低于区间下界 {delta}",
      above: "高于区间上界 {delta}",
      unavailable: "区间不可用",
    },
  },
  ja: {
    conclusion: {
      sectionTitle: "正式結論",
      placeholder:
        "検査開始後、この領域ではまず結論を示し、その後に能力、Prompt、詳細診断の証拠を表示します。",
      whyTitle: "この結論になった理由",
      evidenceTitle: "主要な証拠",
      reasons: {
        range: "指紋レンジとの差分",
        capabilities: "能力差分",
        prompts: "Prompt 単位の差分",
        strength: "証拠強度",
        none: "追加で指摘すべき問題はありません。",
      },
      patterns: {
        rangeInside: "結果は指紋レンジ {range} 内に収まっています。",
        rangeDeviation: "{gap}；指紋レンジ {range}。",
        capabilityLine: "{capability}: 観測 {observed} / 期待 {expected} / 判定 {consistency}。",
        capabilityConsistent: "{capability}: {consistency} ({status})",
        capabilityMismatch:
          "{capability}: {consistency} (観測: {observed}; 指紋期待: {expected})",
        capabilityInsufficient: "{capability}: {consistency}",
        promptNotScoreable: "{prompt}: 採点不可{detail}。",
        promptSimilarity: "{prompt}: 類似度 {similarity}。",
        promptAllClose: "採点可能な Prompt は選択した指紋に概ね近い状態です。",
        metricValue: "{label}{value}。",
        coverageValue: "{answerLabel}{answer} / {reasoningLabel}{reasoning}。",
      },
      labels: {
        running: "結論を生成中",
        configurationError: "設定エラー",
        stopped: "検査停止",
        insufficientEvidence: "証拠不足",
        incompatibleProtocol: "プロトコル異常",
        provisional: "暫定結論",
        highlyConsistent: "高度一致",
        similar: "類似",
        mismatch: "不一致",
        unknown: "不明",
      },
      messages: {
        running: "設定済みエンドポイントから証拠を収集中です。",
        configurationError: "設定が検証を通過しなかったため、信頼できる比較結果を生成できません。",
        stopped: "十分な証拠を集める前に検査が停止しました。",
        insufficientEvidence: "正式な帰属判断に必要な採点可能証拠が不足しています。",
        incompatibleProtocol: "応答プロトコルが不安定なため、指紋比較は信頼できません。",
        provisional: "検査がまだ完了していないため、現在の順位は暫定観測にすぎません。",
        highlyConsistent: "現在の証拠では、対象モデルは選択した指紋モデルと高度に一致しています。",
        similar: "対象モデルは選択した指紋モデルに最も近いものの、高度一致と判断するには証拠が弱い状態です。",
        mismatch: "対象モデルは選択した指紋モデルとは一致せず、別の候補の方が妥当です。",
        unknown: "比較は完了しましたが、信号が弱く、信頼できる帰属判断ができません。",
      },
      firstSentence: {
        highlyConsistent: "対象モデルは選択した指紋モデル {model} と高度に一致しています。",
        similar:
          "対象モデルは選択した指紋モデルに類似していますが、高度一致と判断するには証拠が不足しています。",
        mismatch: "対象モデルは選択した指紋モデルと一致しません。",
        unknown:
          "対象モデルが選択した指紋に属するかは判定できません。",
        provisional:
          "検査はまだ完了していないため、現在の順位は暫定観測にすぎません。",
      },
    },
    capabilityProbe: {
      title: "能力プローブ",
      empty: "能力比較データはまだありません。",
      columns: {
        capability: "能力",
        observed: "観測状態",
        expected: "期待状態",
        consistent: "一致",
      },
      statuses: {
        pending: "未開始",
        running: "検出中",
        supported: "対応",
        accepted_but_ignored: "要求は受理されたが能力は有効化されなかった",
        unsupported: "非対応",
        insufficient_evidence: "証拠不足",
      },
      consistency: {
        yes: "一致",
        no: "不一致",
        unknown: "証拠不足",
      },
    },
    promptProbe: {
      title: "Prompt プローブ",
      empty: "Prompt 比較データはまだありません。",
      columns: {
        prompt: "Prompt",
        status: "状態",
        similarity: "類似度",
        scoreable: "採点可否",
        error: "エラー",
        summary: "評価重点",
      },
      statuses: {
        pending: "未開始",
        running: "実行中",
        completed: "完了",
        failed: "失敗",
        stopped: "停止",
        timeout: "タイムアウト",
        transport_error: "転送エラー",
        unsupported_capability: "未対応能力",
        truncated: "切り詰め",
        invalid_response: "無効応答",
        canonicalization_error: "正規化失敗",
      },
      summaries: {
        waiting: "開始待ち",
        running: "応答を収集中",
        runningWithElapsed: "応答を収集中 · {elapsed}",
        completed: "完了",
        completedWithElapsed: "完了 · {elapsed}",
        failed: "実行失敗",
        stopped: "途中で停止",
      },
    },
    diagnostics: {
      title: "詳細診断情報",
      empty: "証拠が揃うと、ここに詳細診断を表示します。",
      metrics: {
        similarity: "観測類似度",
        fingerprintRange: "指紋レンジ",
        rangeGap: "レンジ差分",
        topCandidate: "最有力候補",
        margin: "差分",
        consistency: "一貫性",
        scoreablePrompts: "採点可能 Prompt 数",
        answerCoverage: "回答カバレッジ",
        reasoningCoverage: "推論カバレッジ",
        protocolStatus: "プロトコル状態",
      },
      sections: {
        protocolIssues: "プロトコル問題",
        hardMismatches: "重大不一致",
        blockingReasons: "阻害要因",
        recommendations: "推奨アクション",
      },
      none: "なし",
    },
    similarModels: {
      title: "類似モデル一覧（Top 5）",
      empty: "比較データが揃うと、ここに最も近いモデル順位が表示されます。",
      columns: {
        rank: "順位",
        model: "モデル",
        score: "スコア",
      },
      selectedFingerprint: "選択した指紋モデル",
    },
    fingerprintMatrix: {
      title: "指紋モデル能力マトリクス",
      empty: "表示できる指紋能力サマリーはまだありません。",
      columns: {
        model: "モデル",
        image: "Image",
        vision: "Vision",
      },
    },
    shared: {
      yes: "はい",
      no: "いいえ",
      unavailable: "-",
    },
    capabilityNames: {
      thinking: "Thinking",
      tools: "Tools",
      streaming: "Streaming",
      image_generation: "Image",
      vision_understanding: "Vision",
    },
    capabilityNotes: {
      thinking: "思考連鎖",
      tools: "ツール呼び出し",
      streaming: "ストリーミング",
      image_generation: "画像生成",
      vision_understanding: "画像理解",
    },
    protocolStatuses: {
      compatible: "互換",
      insufficient_evidence: "証拠不足",
      incompatible_protocol: "プロトコル異常",
    },
    range: {
      inside: "指紋レンジ内",
      below: "下限より {delta} 低い",
      above: "上限より {delta} 高い",
      unavailable: "レンジなし",
    },
  },
}

export function getWorkbenchCopy(locale: LocaleKey) {
  return workbenchCopy[locale] ?? workbenchCopy.en
}

export function formatWorkbench(
  template: string,
  values?: Record<string, string | number | undefined>,
) {
  if (values === undefined) {
    return template
  }

  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const value = values[key]
    return value === undefined ? "" : String(value)
  })
}
