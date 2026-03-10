from __future__ import annotations

from pydantic import Field

from modelfingerprint.contracts._common import ContractModel, SuiteId


class WebFingerprintModel(ContractModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    suite_id: SuiteId
    available: bool

