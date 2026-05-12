from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class TAMEVariant(str, Enum):
    MINIMAL_BASELINE = "minimal_baseline"
    BASELINE_A = "baseline_a"
    BASELINE_M = "baseline_m"
    BASELINE_M_FINAL_GUARD = "baseline_m_final_guard"
    BASELINE_T_PLUS = "baseline_t_plus"
    BASELINE_A_M = "baseline_a_m"
    BASELINE_A_T_PLUS = "baseline_a_t_plus"
    BASELINE_A_T_RECOVERY_ONLY = "baseline_a_t_recovery_only"
    BASELINE_A_T_FINAL_GUARD = "baseline_a_t_final_guard"
    BASELINE_M_T_PLUS = "baseline_m_t_plus"
    FULL_TAME = "full_tame"
    FULL_TAME_FINAL_GUARD = "full_tame_final_guard"
    WO_A_REFLECTION = "wo_a_reflection"
    WO_A_REFLECTION_FINAL_GUARD = "wo_a_reflection_final_guard"
    WO_M_RECOVERY = "wo_m_recovery"
    WO_M_RECOVERY_FINAL_GUARD = "wo_m_recovery_final_guard"
    WO_T_PLUS = "wo_t_plus"
    WO_T_PLUS_FINAL_GUARD = "wo_t_plus_final_guard"


class TAMEConfig(BaseModel):
    """Layer switches for TAME ablation experiments.

    E_core is always enabled because DataSciBench requires code generation and
    execution to produce task artifacts.
    """

    variant: str = TAMEVariant.FULL_TAME.value

    # T layer
    t_min: bool = True
    t_plus: bool = True
    verifier: bool = True
    budget: bool = True
    max_steps: int = 20

    # A layer
    adaptation: bool = True
    planning: bool = True
    reflection: bool = True
    working_memory: bool = True
    check_data: bool = True
    tool_selection: bool = False

    # M layer
    maintenance: bool = True
    checkpoint: bool = True
    resume: bool = True
    recovery: bool = True
    artifact_ledger: bool = True
    final_guard: bool = False

    # E_core
    execution: bool = True
    max_retry: int = 3
    max_react_loop: int = 1

    @classmethod
    def from_variant(cls, variant: str, overrides: dict[str, Any] | None = None) -> "TAMEConfig":
        variant = normalize_variant_name(variant)
        kwargs = _VARIANT_PRESETS[variant].copy()
        kwargs["variant"] = variant
        if overrides:
            kwargs.update({key: value for key, value in overrides.items() if value is not None})
        return cls(**kwargs)

    def as_layer_dict(self) -> dict[str, Any]:
        return {
            "variant": self.variant,
            "T": {"T_min": self.t_min, "T_plus": self.t_plus, "verifier": self.verifier, "budget": self.budget},
            "A": {
                "enabled": self.adaptation,
                "planning": self.planning,
                "reflection": self.reflection,
                "working_memory": self.working_memory,
                "check_data": self.check_data,
                "tool_selection": self.tool_selection,
            },
            "M": {
                "enabled": self.maintenance,
                "checkpoint": self.checkpoint,
                "resume": self.resume,
                "recovery": self.recovery,
                "artifact_ledger": self.artifact_ledger,
                "final_guard": self.final_guard,
            },
            "E": {"E_core": self.execution},
        }


def normalize_variant_name(variant: str) -> str:
    normalized = variant.strip().lower().replace(" ", "_").replace("+", "_")
    aliases = {
        "minimal": TAMEVariant.MINIMAL_BASELINE.value,
        "minimal_baseline": TAMEVariant.MINIMAL_BASELINE.value,
        "baseline+a": TAMEVariant.BASELINE_A.value,
        "baseline_a": TAMEVariant.BASELINE_A.value,
        "baseline+m": TAMEVariant.BASELINE_M.value,
        "baseline_m": TAMEVariant.BASELINE_M.value,
        "baseline+m+final_guard": TAMEVariant.BASELINE_M_FINAL_GUARD.value,
        "baseline_m_final_guard": TAMEVariant.BASELINE_M_FINAL_GUARD.value,
        "baseline+t_plus": TAMEVariant.BASELINE_T_PLUS.value,
        "baseline_t_plus": TAMEVariant.BASELINE_T_PLUS.value,
        "baseline+a+m": TAMEVariant.BASELINE_A_M.value,
        "baseline_a_m": TAMEVariant.BASELINE_A_M.value,
        "baseline+a+t_plus": TAMEVariant.BASELINE_A_T_PLUS.value,
        "baseline_a_t_plus": TAMEVariant.BASELINE_A_T_PLUS.value,
        "baseline+a+t+recovery_only": TAMEVariant.BASELINE_A_T_RECOVERY_ONLY.value,
        "baseline_a_t_recovery_only": TAMEVariant.BASELINE_A_T_RECOVERY_ONLY.value,
        "baseline+a+t_plus+recovery_only": TAMEVariant.BASELINE_A_T_RECOVERY_ONLY.value,
        "baseline_a_t_plus_recovery_only": TAMEVariant.BASELINE_A_T_RECOVERY_ONLY.value,
        "baseline+a+t+final_guard": TAMEVariant.BASELINE_A_T_FINAL_GUARD.value,
        "baseline_a_t_final_guard": TAMEVariant.BASELINE_A_T_FINAL_GUARD.value,
        "baseline+a+t_plus+final_guard": TAMEVariant.BASELINE_A_T_FINAL_GUARD.value,
        "baseline_a_t_plus_final_guard": TAMEVariant.BASELINE_A_T_FINAL_GUARD.value,
        "baseline+m+t_plus": TAMEVariant.BASELINE_M_T_PLUS.value,
        "baseline_m_t_plus": TAMEVariant.BASELINE_M_T_PLUS.value,
        "full": TAMEVariant.FULL_TAME.value,
        "full_tame": TAMEVariant.FULL_TAME.value,
        "full+final_guard": TAMEVariant.FULL_TAME_FINAL_GUARD.value,
        "full_final_guard": TAMEVariant.FULL_TAME_FINAL_GUARD.value,
        "full_tame+final_guard": TAMEVariant.FULL_TAME_FINAL_GUARD.value,
        "full_tame_final_guard": TAMEVariant.FULL_TAME_FINAL_GUARD.value,
        "wo_a_reflection": TAMEVariant.WO_A_REFLECTION.value,
        "w/o_a_reflection": TAMEVariant.WO_A_REFLECTION.value,
        "wo_a_reflection_final_guard": TAMEVariant.WO_A_REFLECTION_FINAL_GUARD.value,
        "w/o_a_reflection_final_guard": TAMEVariant.WO_A_REFLECTION_FINAL_GUARD.value,
        "wo_m_recovery": TAMEVariant.WO_M_RECOVERY.value,
        "w/o_m_recovery": TAMEVariant.WO_M_RECOVERY.value,
        "wo_m_recovery_final_guard": TAMEVariant.WO_M_RECOVERY_FINAL_GUARD.value,
        "w/o_m_recovery_final_guard": TAMEVariant.WO_M_RECOVERY_FINAL_GUARD.value,
        "wo_t_plus": TAMEVariant.WO_T_PLUS.value,
        "w/o_t_plus": TAMEVariant.WO_T_PLUS.value,
        "wo_t_plus_final_guard": TAMEVariant.WO_T_PLUS_FINAL_GUARD.value,
        "w/o_t_plus_final_guard": TAMEVariant.WO_T_PLUS_FINAL_GUARD.value,
    }
    if normalized in aliases:
        return aliases[normalized]
    supported = ", ".join(item.value for item in TAMEVariant)
    raise ValueError(f"Unsupported TAME variant '{variant}'. Supported variants: {supported}")


def tame_contract_prompt(config: TAMEConfig) -> str:
    prompt = [
        "## TAME Thin Harness Contract",
        "- Treat this as a data-science task with a finite stop condition: produce the requested output artifacts in ./.",
        "- Read input data only from the current task directory or ../ as instructed.",
        "- Do not perform destructive filesystem operations, network installs, credential access, or host-level changes.",
    ]
    if config.t_plus:
        prompt.extend(
            [
                "- Before writing code, keep the solution within the task boundary and avoid unrelated exploratory work.",
                "- Prefer deterministic, reproducible code and explicitly create required files.",
                "- If an action seems outside the task scope, choose a safer local alternative.",
                "- Keep generated code compact enough to fit in one complete response.",
            ]
        )
    return "\n".join(prompt) + "\n\n"


_VARIANT_PRESETS: dict[str, dict[str, Any]] = {
    TAMEVariant.MINIMAL_BASELINE.value: {
        "t_plus": False,
        "verifier": False,
        "budget": False,
        "adaptation": False,
        "planning": False,
        "reflection": False,
        "working_memory": False,
        "check_data": False,
        "tool_selection": False,
        "maintenance": False,
        "checkpoint": False,
        "resume": False,
        "recovery": False,
        "artifact_ledger": False,
        "max_retry": 1,
        "max_react_loop": 1,
    },
    TAMEVariant.BASELINE_A.value: {
        "t_plus": False,
        "verifier": False,
        "budget": False,
        "adaptation": True,
        "planning": True,
        "reflection": True,
        "working_memory": True,
        "check_data": True,
        "maintenance": False,
        "checkpoint": False,
        "resume": False,
        "recovery": False,
        "artifact_ledger": False,
    },
    TAMEVariant.BASELINE_M.value: {
        "t_plus": False,
        "verifier": False,
        "budget": False,
        "adaptation": False,
        "planning": False,
        "reflection": False,
        "working_memory": False,
        "check_data": False,
        "maintenance": True,
        "checkpoint": True,
        "resume": True,
        "recovery": True,
        "artifact_ledger": True,
        "max_retry": 2,
    },
    TAMEVariant.BASELINE_M_FINAL_GUARD.value: {
        "t_plus": False,
        "verifier": False,
        "budget": False,
        "adaptation": False,
        "planning": False,
        "reflection": False,
        "working_memory": False,
        "check_data": False,
        "maintenance": True,
        "checkpoint": True,
        "resume": True,
        "recovery": True,
        "artifact_ledger": True,
        "final_guard": True,
        "max_retry": 2,
    },
    TAMEVariant.BASELINE_T_PLUS.value: {
        "t_plus": True,
        "verifier": True,
        "budget": True,
        "adaptation": False,
        "planning": False,
        "reflection": False,
        "working_memory": False,
        "check_data": False,
        "maintenance": False,
        "checkpoint": False,
        "resume": False,
        "recovery": False,
        "artifact_ledger": False,
        "max_retry": 1,
    },
    TAMEVariant.BASELINE_A_M.value: {
        "t_plus": False,
        "verifier": False,
        "budget": False,
        "adaptation": True,
        "planning": True,
        "reflection": True,
        "working_memory": True,
        "check_data": True,
        "maintenance": True,
        "checkpoint": True,
        "resume": True,
        "recovery": True,
        "artifact_ledger": True,
    },
    TAMEVariant.BASELINE_A_T_PLUS.value: {
        "t_plus": True,
        "verifier": True,
        "budget": True,
        "adaptation": True,
        "planning": True,
        "reflection": True,
        "working_memory": True,
        "check_data": True,
        "maintenance": False,
        "checkpoint": False,
        "resume": False,
        "recovery": False,
        "artifact_ledger": False,
    },
    TAMEVariant.BASELINE_A_T_RECOVERY_ONLY.value: {
        "t_plus": True,
        "verifier": True,
        "budget": True,
        "adaptation": True,
        "planning": True,
        "reflection": True,
        "working_memory": True,
        "check_data": True,
        "maintenance": False,
        "checkpoint": False,
        "resume": False,
        "recovery": True,
        "artifact_ledger": False,
    },
    TAMEVariant.BASELINE_A_T_FINAL_GUARD.value: {
        "t_plus": True,
        "verifier": True,
        "budget": True,
        "adaptation": True,
        "planning": True,
        "reflection": True,
        "working_memory": True,
        "check_data": True,
        "maintenance": False,
        "checkpoint": False,
        "resume": False,
        "recovery": False,
        "artifact_ledger": False,
        "final_guard": True,
    },
    TAMEVariant.BASELINE_M_T_PLUS.value: {
        "t_plus": True,
        "verifier": True,
        "budget": True,
        "adaptation": False,
        "planning": False,
        "reflection": False,
        "working_memory": False,
        "check_data": False,
        "maintenance": True,
        "checkpoint": True,
        "resume": True,
        "recovery": True,
        "artifact_ledger": True,
        "max_retry": 2,
    },
    TAMEVariant.FULL_TAME.value: {},
    TAMEVariant.FULL_TAME_FINAL_GUARD.value: {
        "final_guard": True,
    },
    TAMEVariant.WO_A_REFLECTION.value: {
        "reflection": False,
    },
    TAMEVariant.WO_A_REFLECTION_FINAL_GUARD.value: {
        "reflection": False,
        "final_guard": True,
    },
    TAMEVariant.WO_M_RECOVERY.value: {
        "checkpoint": False,
        "resume": False,
        "recovery": False,
    },
    TAMEVariant.WO_M_RECOVERY_FINAL_GUARD.value: {
        "checkpoint": False,
        "resume": False,
        "recovery": False,
        "final_guard": True,
    },
    TAMEVariant.WO_T_PLUS.value: {
        "t_plus": False,
        "verifier": False,
        "budget": False,
    },
    TAMEVariant.WO_T_PLUS_FINAL_GUARD.value: {
        "t_plus": False,
        "verifier": False,
        "budget": False,
        "final_guard": True,
    },
}
