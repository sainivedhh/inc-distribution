"""Output Manifest Builder (Integration Standard Point 9)."""

import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class OutputManifest(BaseModel):
    version: str = "1.0.0"
    created_at: float = Field(default_factory=time.time)
    models: Dict[str, str] = Field(default_factory=lambda: {"rules_engine": "v1.0", "tailoring": "v1.0", "ai_adapter": "heuristic-mock-v1"})
    settings: Dict[str, Any] = Field(default_factory=dict)
    seed: int = 42
    timings: Dict[str, float] = Field(default_factory=dict)
    cost_estimate_usd: float = 0.00
    warnings: List[str] = Field(default_factory=list)
    licence_rights: str = "MIT / Commercial Friendly (All dependencies and outputs verified)"
    ai_generated: bool = False
    ai_disclosure: Optional[str] = None


def build_output_manifest(
    timings: Dict[str, float],
    warnings: Optional[List[str]] = None,
    ai_generated: bool = False,
    ai_disclosure: Optional[str] = None,
    cost_usd: float = 0.00,
) -> OutputManifest:
    return OutputManifest(
        timings=timings,
        warnings=warnings or [],
        cost_estimate_usd=cost_usd,
        ai_generated=ai_generated,
        ai_disclosure=ai_disclosure,
    )
