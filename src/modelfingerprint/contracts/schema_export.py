from __future__ import annotations

import json
from pathlib import Path

from modelfingerprint.contracts._common import ContractModel
from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.comparison import ComparisonArtifact
from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.settings import resolve_repository_root

SCHEMA_EXPORTS = {
    "prompt": Path("schemas/prompt.schema.json"),
    "endpoint": Path("schemas/endpoint.schema.json"),
    "run": Path("schemas/run.schema.json"),
    "profile": Path("schemas/profile.schema.json"),
    "calibration": Path("schemas/calibration.schema.json"),
    "comparison": Path("schemas/comparison.schema.json"),
}

SCHEMA_MODELS: dict[str, type[ContractModel]] = {
    "prompt": PromptDefinition,
    "endpoint": EndpointProfile,
    "run": RunArtifact,
    "profile": ProfileArtifact,
    "calibration": CalibrationArtifact,
    "comparison": ComparisonArtifact,
}


def export_schemas(root: Path | None = None) -> dict[str, Path]:
    repository_root = resolve_repository_root(root)
    exported: dict[str, Path] = {}

    for name, model in SCHEMA_MODELS.items():
        schema_path = repository_root / SCHEMA_EXPORTS[name]
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path.write_text(
            json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        exported[name] = schema_path

    return exported
