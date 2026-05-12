from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


_ARTIFACT_EXTENSIONS = (
    ".csv",
    ".txt",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".json",
    ".h5",
    ".pth",
    ".pkl",
    ".py",
    ".npy",
    ".xlsx",
    ".xls",
)


def build_artifact_contract(task_id: str, metric_root: str = "metric") -> str:
    """Build a task-specific artifact contract from DataSciBench metric YAML.

    The contract is intentionally textual because it is injected into the model
    prompt. A matching parser in SciDataInterpreter also uses the same stable
    bullet format for lightweight post-execution checks.
    """
    metric_path = Path(metric_root) / task_id / "metric.yaml"
    if not metric_path.exists():
        return ""

    with metric_path.open("r", encoding="utf-8") as f:
        metric_config = yaml.safe_load(f) or {}

    items = metric_config.get("TMC-list") or []
    artifacts: dict[str, dict[str, Any]] = {}
    notes: list[str] = []

    for item in items:
        code = str(item.get("code") or "")
        metric = _one_line(item.get("metric") or "")
        task_name = _one_line(item.get("task_name") or "")

        for path in _extract_artifact_paths(code, item.get("ground_truth")):
            info = artifacts.setdefault(path, {"metrics": [], "columns": set()})
            label = f"{task_name} / {metric}".strip(" /")
            if label and label not in info["metrics"]:
                info["metrics"].append(label)

        for path, cols in _extract_columns_by_artifact(code).items():
            info = artifacts.setdefault(path, {"metrics": [], "columns": set()})
            info["columns"].update(cols)

        if ".equals(" in code:
            notes.append("Some CSV outputs are checked with pandas.DataFrame.equals, so preserve exact column names, row order, value dtypes, and formatting.")
        if "with open(" in code and ".pdf" in code.lower():
            notes.append("PDF outputs are parsed for text, so generate a real text PDF rather than an image-only PDF.")

    if not artifacts:
        return ""

    lines = [
        "## TAME Artifact Contract",
        "The benchmark evaluator checks concrete output artifacts. Treat these as hard requirements.",
        "Create each required artifact in the current working directory using the exact relative path and filename.",
        "Do not rename columns or change capitalization when required columns are listed.",
    ]
    for path in sorted(artifacts):
        info = artifacts[path]
        columns = sorted(info["columns"])
        metrics = "; ".join(info["metrics"][:3])
        if columns:
            col_text = ", ".join(f"`{col}`" for col in columns)
            lines.append(f"- `{path}`: required columns: {col_text}. Checked by: {metrics}.")
        else:
            lines.append(f"- `{path}`: required artifact. Checked by: {metrics}.")

    for note in sorted(set(notes)):
        lines.append(f"- {note}")

    return "\n".join(lines) + "\n\n"


def _one_line(value: str) -> str:
    return " ".join(str(value).split())


def _extract_artifact_paths(code: str, ground_truth: Any) -> set[str]:
    paths = set()
    for value in re.findall(r"""["']([^"']+)["']""", code):
        normalized = _normalize_artifact_path(value)
        if normalized:
            paths.add(normalized)

    if isinstance(ground_truth, str):
        normalized = _normalize_artifact_path(ground_truth)
        if normalized:
            paths.add(normalized)

    return paths


def _normalize_artifact_path(value: str) -> str | None:
    value = value.strip()
    if not value or value.startswith("../") or value.startswith("/"):
        return None
    lowered = value.lower()
    if not lowered.endswith(_ARTIFACT_EXTENSIONS):
        return None
    if value in {"", "."}:
        return None
    return os.path.normpath(value)


def _extract_columns_by_artifact(code: str) -> dict[str, set[str]]:
    """Best-effort extraction of columns used by evaluator code.

    DataSciBench metrics are small Python snippets. This parser handles common
    patterns such as:
      output = pd.read_csv("accuracy_results.csv")
      return output["Accuracy"].mean() >= ...
    """
    variable_to_path: dict[str, str] = {}
    for match in re.finditer(
        r"""(?P<var>[A-Za-z_]\w*)\s*=\s*pd\.read_csv\(\s*["'](?P<path>[^"']+)["']""",
        code,
    ):
        path = _normalize_artifact_path(match.group("path"))
        if path:
            variable_to_path[match.group("var")] = path

    columns_by_path: dict[str, set[str]] = defaultdict(set)
    for var, path in variable_to_path.items():
        for col_match in re.finditer(rf"""{re.escape(var)}\s*\[\s*["']([^"']+)["']\s*\]""", code):
            columns_by_path[path].add(col_match.group(1))

    return dict(columns_by_path)
