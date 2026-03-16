export type LocaleKey = "en" | "zh-CN" | "ja"

export type MessageKey =
  | "app.title"
  | "app.tagline"
  | "app.subtitle"
  | "actions.startCheck"
  | "actions.theme"
  | "actions.language"
  | "actions.changeTheme"
  | "actions.changeLanguage"
  | "actions.openGithub"
  | "actions.stopCheck"
  | "theme.light"
  | "theme.dark"
  | "theme.system"
  | "locale.english"
  | "locale.simplifiedChinese"
  | "locale.japanese"
  | "sections.configuration"
  | "sections.workbench"
  | "sections.result"
  | "sections.howItWorks"
  | "howItWorks.intro"
  | "howItWorks.training.title"
  | "howItWorks.training.description"
  | "howItWorks.comparison.title"
  | "howItWorks.comparison.description"
  | "howItWorks.conclusion.title"
  | "howItWorks.conclusion.description"
  | "form.selectFingerprintPlaceholder"
  | "validation.apiKeyRequired"
  | "validation.baseUrlInvalid"
  | "validation.modelNameRequired"
  | "validation.fingerprintRequired"
  | "state.empty.title"
  | "state.empty.description"
  | "state.workbenchPlaceholder"
  | "state.configurationError.title"
  | "state.configurationError.description"
  | "state.stopped.title"
  | "state.stopped.description"
  | "state.running.title"
  | "state.running.description"
  | "state.incompatibleProtocol.title"
  | "state.incompatibleProtocol.description"
  | "state.insufficientEvidence.title"
  | "state.insufficientEvidence.description"
  | "state.provisional.title"
  | "state.provisional.description"
  | "state.provisional.withCandidate"
  | "state.formalResult.title"
  | "state.formalResult.description"
  | "state.formalResult.withCandidate"
  | "form.apiKey"
  | "form.baseUrl"
  | "form.modelName"
  | "form.fingerprintModel"
  | "form.securityNote"

export const messages: Record<LocaleKey, Record<MessageKey, string>> = {
  en: {
    "app.title": "Model Fingerprint",
    "app.tagline": "Verify model identity and detect downgrades or swaps",
    "app.subtitle": "Identify whether a model is what it claims to be through fingerprint comparison.",
    "actions.startCheck": "Start Check",
    "actions.theme": "Theme",
    "actions.language": "Language",
    "actions.changeTheme": "Change theme",
    "actions.changeLanguage": "Change language",
    "actions.openGithub": "Open GitHub repository",
    "actions.stopCheck": "Stop Check",
    "theme.light": "Light",
    "theme.dark": "Dark",
    "theme.system": "System",
    "locale.english": "English",
    "locale.simplifiedChinese": "Simplified Chinese",
    "locale.japanese": "Japanese",
    "sections.configuration": "Configuration",
    "sections.workbench": "Workbench",
    "sections.result": "Result",
    "sections.howItWorks": "How it works",
    "howItWorks.intro":
      "Combine standard fingerprint training with live response comparison to verify whether the target model matches its claimed identity.",
    "howItWorks.training.title": "Fingerprint training",
    "howItWorks.training.description":
      "Build standard fingerprints from large-scale official model responses, capturing stable signals across structure, capability, and style.",
    "howItWorks.comparison.title": "Fingerprint comparison",
    "howItWorks.comparison.description":
      "Send five high-information prompts to the target endpoint and compare the extracted signals against preset fingerprint models.",
    "howItWorks.conclusion.title": "Conclusion output",
    "howItWorks.conclusion.description":
      "Use completion coverage and match consistency to output similarity, confidence interval, and a final verdict. When evidence is limited, show only provisional observations.",
    "form.selectFingerprintPlaceholder": "Select a fingerprint",
    "validation.apiKeyRequired": "API Key is required.",
    "validation.baseUrlInvalid": "Base URL must be a valid URL.",
    "validation.modelNameRequired": "Model name is required.",
    "validation.fingerprintRequired": "Choose a fingerprint model.",
    "state.empty.title": "No active check",
    "state.empty.description":
      "Enter endpoint details, choose a fingerprint model, and start a live five-prompt check.",
    "state.workbenchPlaceholder":
      "This panel will render the global run state, current probe, per-prompt status, and result conclusion.",
    "state.configurationError.title": "Unable to start check",
    "state.configurationError.description":
      "The endpoint configuration did not pass validation. Update the input fields and retry.",
    "state.stopped.title": "Check stopped",
    "state.stopped.description":
      "This run was stopped before enough evidence was collected for a final conclusion.",
    "state.running.title": "Running model fingerprint check",
    "state.running.description":
      "The workbench is collecting live evidence from the configured endpoint.",
    "state.incompatibleProtocol.title": "Incompatible protocol",
    "state.incompatibleProtocol.description":
      "The endpoint did not satisfy the expected response protocol consistently. This does not prove a model mismatch.",
    "state.insufficientEvidence.title": "Insufficient evidence",
    "state.insufficientEvidence.description":
      "The run finished with too little usable data to judge whether the endpoint matches the selected fingerprint.",
    "state.provisional.title": "Provisional observation",
    "state.provisional.description":
      "Partial evidence is available, but the run is incomplete and cannot support a final verdict.",
    "state.provisional.withCandidate":
      "Partial evidence currently looks closer to {candidate}. Treat this as a temporary observation, not a final conclusion.",
    "state.formalResult.title": "Formal conclusion",
    "state.formalResult.description":
      "All prompts completed and the run is ready for a final comparison summary.",
    "state.formalResult.withCandidate":
      "All prompts completed. The endpoint can now be compared formally against {fingerprint}, with {candidate} as the nearest candidate if applicable.",
    "form.apiKey": "API Key",
    "form.baseUrl": "Base URL",
    "form.modelName": "Model Name",
    "form.fingerprintModel": "Fingerprint Model",
    "form.securityNote": "Your API key is used only for this check and is not stored after the request completes.",
  },
  "zh-CN": {
    "app.title": "模型指纹识别",
    "app.tagline": "验证模型身份，识别降智与替换",
    "app.subtitle": "通过模型指纹比对，判断一个模型是否与其声明身份一致。",
    "actions.startCheck": "开始检查",
    "actions.theme": "主题",
    "actions.language": "语言",
    "actions.changeTheme": "切换主题",
    "actions.changeLanguage": "切换语言",
    "actions.openGithub": "打开 GitHub 仓库",
    "actions.stopCheck": "停止检测",
    "theme.light": "浅色",
    "theme.dark": "深色",
    "theme.system": "跟随系统",
    "locale.english": "English",
    "locale.simplifiedChinese": "简体中文",
    "locale.japanese": "日本語",
    "sections.configuration": "配置",
    "sections.workbench": "检测工作台",
    "sections.result": "检测结果",
    "sections.howItWorks": "如何工作",
    "howItWorks.intro": "通过标准指纹训练与在线响应比对，判断目标模型是否与声明身份一致。",
    "howItWorks.training.title": "指纹训练",
    "howItWorks.training.description":
      "基于官方模型的大规模标准响应，提取结构、能力与风格等稳定特征，生成标准指纹。",
    "howItWorks.comparison.title": "指纹比对",
    "howItWorks.comparison.description":
      "向待测模型发送 5 个高信息密度 Prompt，提取同维度信号，与预置指纹模型进行匹配计算。",
    "howItWorks.conclusion.title": "输出结论",
    "howItWorks.conclusion.description":
      "根据完成题数和匹配结果，输出匹配度、可信区间与最终判断；证据不足时只给临时观察，不强行下结论。",
    "form.selectFingerprintPlaceholder": "选择一个指纹",
    "validation.apiKeyRequired": "API Key 为必填项。",
    "validation.baseUrlInvalid": "Base URL 必须是有效的 URL。",
    "validation.modelNameRequired": "模型名称为必填项。",
    "validation.fingerprintRequired": "请选择一个指纹模型。",
    "state.empty.title": "当前无检测任务",
    "state.empty.description": "输入接口信息、选择指纹模型后，即可开始 5 题在线检测。",
    "state.workbenchPlaceholder": "该区域将展示全局运行状态、当前探测步骤、逐题状态和最终结论。",
    "state.configurationError.title": "无法开始检测",
    "state.configurationError.description": "当前接口配置未通过校验，请更新输入后重试。",
    "state.stopped.title": "检测已停止",
    "state.stopped.description": "本轮检测在收集到足够证据形成最终结论前被停止。",
    "state.running.title": "正在执行模型指纹检测",
    "state.running.description": "工作台正在从当前配置的接口中收集实时证据。",
    "state.incompatibleProtocol.title": "接口协议不兼容",
    "state.incompatibleProtocol.description":
      "当前接口未能持续满足预期响应协议要求，这不等同于模型身份不匹配。",
    "state.insufficientEvidence.title": "证据不足",
    "state.insufficientEvidence.description": "本轮检测获得的有效数据过少，无法判断接口是否匹配所选指纹模型。",
    "state.provisional.title": "临时观察",
    "state.provisional.description": "当前已有部分可用证据，但检测尚未完整完成，不能形成正式结论。",
    "state.provisional.withCandidate": "当前部分证据更接近 {candidate}，请将其视为临时观察，而不是最终结论。",
    "state.formalResult.title": "正式结论",
    "state.formalResult.description": "所有题目均已完成，本轮检测可以输出正式比对结论。",
    "state.formalResult.withCandidate": "所有题目均已完成。现在可以针对 {fingerprint} 形成正式比对结论，如有需要，也可将 {candidate} 作为最接近的候选模型。",
    "form.apiKey": "API Key",
    "form.baseUrl": "Base URL",
    "form.modelName": "模型名称",
    "form.fingerprintModel": "指纹模型",
    "form.securityNote": "API Key 仅用于本次检测，请求完成后即释放，不会持久化保存。",
  },
  ja: {
    "app.title": "モデル指紋識別",
    "app.tagline": "モデルの真正性を検証し、劣化や差し替えを検知",
    "app.subtitle": "モデル指紋比較により、対象モデルが申告どおりのモデルかを判定します。",
    "actions.startCheck": "検査開始",
    "actions.theme": "テーマ",
    "actions.language": "言語",
    "actions.changeTheme": "テーマを変更",
    "actions.changeLanguage": "言語を変更",
    "actions.openGithub": "GitHub リポジトリを開く",
    "actions.stopCheck": "検査を停止",
    "theme.light": "ライト",
    "theme.dark": "ダーク",
    "theme.system": "システム",
    "locale.english": "English",
    "locale.simplifiedChinese": "簡体字中国語",
    "locale.japanese": "日本語",
    "sections.configuration": "設定",
    "sections.workbench": "検査ワークベンチ",
    "sections.result": "検査結果",
    "sections.howItWorks": "仕組み",
    "howItWorks.intro":
      "標準指紋の学習結果とオンライン応答比較を組み合わせ、対象モデルが申告どおりかを判定します。",
    "howItWorks.training.title": "指紋学習",
    "howItWorks.training.description":
      "公式モデルの大規模な標準応答から、構造・能力・文体にまたがる安定した特徴を抽出し、標準指紋を構築します。",
    "howItWorks.comparison.title": "指紋比較",
    "howItWorks.comparison.description":
      "対象モデルに 5 つの高情報密度 Prompt を送信し、同一軸の信号を抽出して、プリセット指紋モデルと照合します。",
    "howItWorks.conclusion.title": "結論出力",
    "howItWorks.conclusion.description":
      "完了題数と一致度に基づいて、類似度・信頼区間・最終判断を出力します。証拠が不足する場合は暫定観測のみを表示します。",
    "form.selectFingerprintPlaceholder": "指紋を選択",
    "validation.apiKeyRequired": "API Key は必須です。",
    "validation.baseUrlInvalid": "Base URL は有効な URL である必要があります。",
    "validation.modelNameRequired": "モデル名は必須です。",
    "validation.fingerprintRequired": "指紋モデルを選択してください。",
    "state.empty.title": "進行中の検査はありません",
    "state.empty.description": "エンドポイント情報を入力し、指紋モデルを選択すると、5 問のライブ検査を開始できます。",
    "state.workbenchPlaceholder":
      "この領域には、全体の実行状態、現在のプローブ、各プロンプトの状態、最終結論が表示されます。",
    "state.configurationError.title": "検査を開始できません",
    "state.configurationError.description": "現在のエンドポイント設定は検証に失敗しました。入力内容を更新して再試行してください。",
    "state.stopped.title": "検査を停止しました",
    "state.stopped.description": "十分な証拠が集まる前に、この検査は停止されました。",
    "state.running.title": "モデル指紋検査を実行中",
    "state.running.description": "ワークベンチが設定済みエンドポイントからリアルタイム証拠を収集中です。",
    "state.incompatibleProtocol.title": "プロトコル非互換",
    "state.incompatibleProtocol.description":
      "エンドポイントが期待される応答プロトコルを継続的に満たしませんでした。これはモデル不一致の証拠ではありません。",
    "state.insufficientEvidence.title": "証拠不足",
    "state.insufficientEvidence.description": "利用可能なデータが少なすぎるため、選択した指紋モデルとの一致を判断できません。",
    "state.provisional.title": "暫定観測",
    "state.provisional.description": "一部の有効な証拠はありますが、検査が完了していないため正式な結論は出せません。",
    "state.provisional.withCandidate":
      "現在の部分証拠では {candidate} により近く見えますが、これは最終結論ではなく暫定観測です。",
    "state.formalResult.title": "正式結論",
    "state.formalResult.description": "すべてのプロンプトが完了し、正式な比較サマリーを出せる状態です。",
    "state.formalResult.withCandidate":
      "すべてのプロンプトが完了しました。{fingerprint} に対して正式比較を行え、必要に応じて {candidate} を最も近い候補として扱えます。",
    "form.apiKey": "API Key",
    "form.baseUrl": "Base URL",
    "form.modelName": "モデル名",
    "form.fingerprintModel": "指紋モデル",
    "form.securityNote": "API Key は今回の検査にのみ使用され、リクエスト完了後に保持されません。",
  },
}
