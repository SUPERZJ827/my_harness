from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


def select_relevant_artifacts(expected_specs: dict[str, list[str]], code: str) -> dict[str, list[str]]:
    if not expected_specs:
        return {}
    relevant = {
        path: columns
        for path, columns in expected_specs.items()
        if path in code or os.path.basename(path) in code
    }
    return relevant or expected_specs


def collect_artifact_status(expected_specs: dict[str, list[str]]) -> dict:
    artifacts = []
    present_paths = []
    missing_paths = []
    schema_errors = []
    for path, columns in expected_specs.items():
        exists = os.path.exists(path)
        item = {
            "path": path,
            "exists": exists,
            "required_columns": list(columns),
            "present_columns": [],
            "missing_columns": [],
        }
        if exists:
            present_paths.append(path)
            if columns and path.lower().endswith(".csv"):
                try:
                    import pandas as pd

                    df = pd.read_csv(path, nrows=5)
                    present_columns = [str(col) for col in df.columns]
                    missing_columns = [col for col in columns if col not in present_columns]
                    item["present_columns"] = present_columns
                    item["missing_columns"] = missing_columns
                    if missing_columns:
                        schema_errors.append({"path": path, "missing_columns": missing_columns})
                except Exception as exc:
                    item["inspect_error"] = str(exc)
        else:
            missing_paths.append(path)
        artifacts.append(item)
    return {
        "artifacts": artifacts,
        "expected_paths": [item["path"] for item in artifacts],
        "present_paths": present_paths,
        "missing_paths": missing_paths,
        "schema_errors": schema_errors,
    }


def snapshot_artifacts(paths: list[str], backup_root: str, attempt_id: str) -> dict[str, dict[str, str | bool]]:
    backup_dir = Path(backup_root) / attempt_id
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    snapshot: dict[str, dict[str, str | bool]] = {}
    for index, path in enumerate(paths):
        src = Path(path)
        entry = {"existed": src.exists(), "backup_path": ""}
        if src.exists():
            backup_path = backup_dir / f"{index}_{src.name}"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, backup_path)
            entry["backup_path"] = str(backup_path)
        snapshot[path] = entry
    return snapshot


def rollback_artifacts(snapshot: dict[str, dict[str, str | bool]]) -> None:
    for path, entry in snapshot.items():
        target = Path(path)
        existed = bool(entry.get("existed"))
        backup_path = str(entry.get("backup_path") or "")
        if existed and backup_path:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target)
        elif not existed and target.exists():
            if target.is_file():
                target.unlink()


def write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def read_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
