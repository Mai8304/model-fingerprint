[English](./README.md) | 简体中文

# Model Fingerprint

一个基于文件产物的 CLI，用于验证两个 LLM endpoint 是否很可能暴露的是同一个底层模型。

## 它验证什么

Model Fingerprint 面向平台工程团队，帮助你在不同供应商名称、包装方式或协议行为存在差异时，判断两个 LLM endpoint 是否很可能代表同一个底层模型。

典型场景：

- 验证供应商关于模型身份的声明
- 将托管 endpoint 与内部基线指纹做对比
- 跟踪供应商切换或版本变更后的行为漂移

## 工作原理

Model Fingerprint 通过版本化 probe suite 和文件化产物，比较两个 endpoint 是否很可能暴露的是同一个底层模型。

1. 发布一套 probe suite。版本化 suite 定义了用于产生可比较信号的 prompts 和 extractors。
2. 对目标 endpoint 运行 suite。每次执行都会产出 run artifact，其中包含归一化输出、coverage 和协议观测结果。
3. 用重复运行结果构建 reference profile。profile 会把同一已知模型的多次 run 聚合成更稳定的参考指纹。
4. 用已知基线做阈值校准。calibration 会针对该 suite 推导阈值，而不是依赖固定的全局 cutoff。
5. 用 suspect run 对比 reference profiles。比较结果会输出 similarity、coverage、protocol status 和最终 verdict。

模型身份相似性与协议兼容性会被分开报告。

## 快速开始

前置要求：

- Python 3.12+
- `uv`

下面这组命令会使用仓库内置的 `examples/quickstart/quick-check-v3/` 离线样例，完整跑通 `quick-check-v3` 工作流。

```bash
uv sync --extra dev

RUN_DATE=2026-03-11
EXAMPLES=examples/quickstart/quick-check-v3

uv run python -m modelfingerprint.cli validate-prompts --root .
uv run python -m modelfingerprint.cli validate-endpoints --root .

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label glm-5-a1 \
  --claimed-model glm-5 \
  --fixture-responses "$EXAMPLES/glm-5-a1.json" \
  --run-date "$RUN_DATE"

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label glm-5-a2 \
  --claimed-model glm-5 \
  --fixture-responses "$EXAMPLES/glm-5-a2.json" \
  --run-date "$RUN_DATE"

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label claude-ops-4.6-a1 \
  --claimed-model claude-ops-4.6 \
  --fixture-responses "$EXAMPLES/claude-ops-4.6-a1.json" \
  --run-date "$RUN_DATE"

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label claude-ops-4.6-a2 \
  --claimed-model claude-ops-4.6 \
  --fixture-responses "$EXAMPLES/claude-ops-4.6-a2.json" \
  --run-date "$RUN_DATE"

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label suspect-v3 \
  --claimed-model glm-5 \
  --fixture-responses "$EXAMPLES/suspect.json" \
  --run-date "$RUN_DATE"

uv run python -m modelfingerprint.cli build-profile \
  --root . \
  --model-id glm-5 \
  --run "runs/$RUN_DATE/glm-5-a1.quick-check-v3.json" \
  --run "runs/$RUN_DATE/glm-5-a2.quick-check-v3.json"

uv run python -m modelfingerprint.cli build-profile \
  --root . \
  --model-id claude-ops-4.6 \
  --run "runs/$RUN_DATE/claude-ops-4.6-a1.quick-check-v3.json" \
  --run "runs/$RUN_DATE/claude-ops-4.6-a2.quick-check-v3.json"

uv run python -m modelfingerprint.cli calibrate \
  --root . \
  --profile profiles/quick-check-v3/glm-5.json \
  --profile profiles/quick-check-v3/claude-ops-4.6.json \
  --run "runs/$RUN_DATE/glm-5-a1.quick-check-v3.json" \
  --run "runs/$RUN_DATE/glm-5-a2.quick-check-v3.json" \
  --run "runs/$RUN_DATE/claude-ops-4.6-a1.quick-check-v3.json" \
  --run "runs/$RUN_DATE/claude-ops-4.6-a2.quick-check-v3.json"

uv run python -m modelfingerprint.cli compare \
  --run "runs/$RUN_DATE/suspect-v3.quick-check-v3.json" \
  --profile profiles/quick-check-v3/glm-5.json \
  --profile profiles/quick-check-v3/claude-ops-4.6.json \
  --calibration calibration/quick-check-v3.json \
  --artifact-json > comparison.json
```

生成的 `comparison.json` 应该会把 `glm-5` 排在第一，并给出兼容协议的结果，例如：

```json
{
  "summary": {
    "top1_model": "glm-5",
    "verdict": "match"
  },
  "coverage": {
    "protocol_status": "compatible"
  }
}
```

如果你只想看精简版对比摘要，可以把 `--artifact-json` 换成 `--json`。

## 如何解读结果

- `top1_model` 和 `top1_similarity` 表示最接近的 reference profile。
- `content_similarity` 和 `capability_similarity` 是最主要的比较信号摘要。
- `answer_coverage_ratio`、`reasoning_coverage_ratio` 和 `capability_coverage_ratio` 表示这套 suite 中有多少证据可用于判断。
- `protocol_status` 和 `verdict` 需要一起看。协议问题是操作层面的证据，不会自动证明底层模型不同。

## 限制

- Model Fingerprint 给出的是证据，不是数学意义上的身份证明。
- verdict 的质量依赖所选 suite 以及用于 calibration 的基线 runs。
- 如果 coverage 很低，即使 similarity 很高，也应谨慎解释。
- 协议不兼容并不自动意味着底层模型不同。

## CLI 总览

- `probe-capabilities`：探测 live endpoint 的能力信号
- `validate-prompts`：校验 prompt 定义、suite 引用和发布子集关系
- `validate-endpoints`：校验 endpoint-profile YAML 文件
- `show-suite`：查看磁盘上的已发布 suite
- `show-run`：查看已存储的 run artifact
- `show-profile`：查看已存储的 profile artifact
- `run-suite`：以离线 fixture 模式或 live endpoint 模式执行 suite
- `build-profile`：将多次 run 聚合为 reference profile artifact
- `calibrate`：基于已知基线推导 suite 专属阈值
- `compare`：将 suspect run 与 reference profiles 对比，并输出摘要或完整 artifact

## 仓库结构

- `examples/quickstart/quick-check-v3/`：对外 quickstart 使用的离线 fixtures
- `prompt-bank/`：prompt 定义和发布套件
- `endpoint-profiles/`：按 dialect 组织的 endpoint capability profiles
- `extractors/`：extractor 描述
- `schemas/`：artifact contract 的 JSON Schema
- `src/modelfingerprint/`：CLI、contracts、services、transports 和 adapters
- `tests/`：contract、unit 和 end-to-end 测试

## 开发

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests
uv run mypy src
```

## 更多文档

- `docs/apis/`：稳定的 API 与 contract 参考文档
