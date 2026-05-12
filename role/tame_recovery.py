from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RecoverySignal:
    error_type: str
    summary: str
    guidance: str


def classify_failure(result: str) -> RecoverySignal:
    text = str(result)
    lowered = text.lower()

    if "numpy' has no attribute 'object'" in text or "numpy' has no attribute 'int'" in text:
        return RecoverySignal(
            error_type="numpy_alias_error",
            summary="Deprecated NumPy alias triggered a runtime failure.",
            guidance=(
                "Do not use deprecated NumPy aliases such as np.object, np.int, np.float, or np.bool. "
                "Use built-in object/int/float/bool or explicit NumPy dtypes such as np.float32."
            ),
        )

    if "can't convert np.ndarray of type numpy.object_" in lowered or "dtype numpy.object_" in lowered:
        return RecoverySignal(
            error_type="tensor_dtype_error",
            summary="A tensor or numeric array was built from object/string dtype data.",
            guidance=(
                "Before converting arrays to torch or NumPy numeric tensors, clean the dataframe and make every "
                "feature numeric. Use pd.to_numeric(..., errors='coerce'), fill/drop missing values, or encode "
                "categorical columns before tensor conversion."
            ),
        )

    if "predict_proba" in text and "index 1 is out of bounds for axis 1 with size 1" in text:
        return RecoverySignal(
            error_type="single_class_proba_error",
            summary="predict_proba assumed two classes, but the fitted model exposed only one class.",
            guidance=(
                "Handle single-class training or prediction safely. Check model.classes_ and the shape of "
                "predict_proba before indexing column 1. If only one class exists, write robust fallback metrics "
                "and still produce the required evaluation artifact."
            ),
        )

    if "missing required artifact:" in lowered:
        return RecoverySignal(
            error_type="missing_artifact_error",
            summary="Required output artifacts were not generated.",
            guidance=(
                "Prioritize writing every required artifact to the exact required relative path before adding extra "
                "analysis. If a later metric fails, still emit the required output files whenever possible."
            ),
        )

    if "missing required columns:" in lowered:
        return RecoverySignal(
            error_type="missing_column_error",
            summary="A required artifact was generated with the wrong schema.",
            guidance=(
                "Preserve exact required column names, capitalization, and CSV schema from the artifact contract."
            ),
        )

    if "no such file or directory" in lowered:
        match = re.search(r"No such file or directory: '([^']+)'", text)
        target = match.group(1) if match else "required artifact"
        return RecoverySignal(
            error_type="missing_file_error",
            summary=f"Execution expected a missing file: {target}.",
            guidance=(
                "Confirm every required input/output path exists at the expected relative location. Do not assume "
                "alternative filenames or directories."
            ),
        )

    return RecoverySignal(
        error_type="execution_error",
        summary="Execution failed with an uncategorized runtime error.",
        guidance=(
            "Focus on the failing traceback, make the smallest code correction that resolves it, and preserve the "
            "required artifacts and schema."
        ),
    )


def build_recovery_prompt(
    signal: RecoverySignal,
    result: str,
    missing_artifacts: list[str],
    retry_index: int,
) -> str:
    missing = ", ".join(missing_artifacts) if missing_artifacts else "none"
    traceback_preview = str(result)[-1200:]
    return (
        "## TAME Recovery Hint\n"
        f"- Retry attempt: {retry_index + 1}\n"
        f"- Error type: {signal.error_type}\n"
        f"- Failure summary: {signal.summary}\n"
        f"- Missing artifacts: {missing}\n"
        f"- Mandatory fix guidance: {signal.guidance}\n"
        "- Keep the next patch local and targeted. Preserve already-correct artifacts when possible.\n"
        "- If metric computation is fragile, emit the required output file with robust fallback handling instead of crashing.\n"
        f"- Traceback excerpt:\n{traceback_preview}\n"
    )
