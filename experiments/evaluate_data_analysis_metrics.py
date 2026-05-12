import argparse
import csv
import json
import math
import re
from pathlib import Path
from statistics import mean, median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MISSING = "-"


def parse_args():
    parser = argparse.ArgumentParser(description="Summarize Data Analysis TAME metrics for one or more result variants.")
    parser.add_argument("--results-parent", required=True, help="Directory containing variant result folders.")
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"), help="Directory containing task metadata.")
    parser.add_argument("--task-prefix", default="", help="Optional task prefix filter, e.g. dabstep_ or dsbench_da_.")
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Summary CSV path. Defaults to <results-parent>/data_analysis_metrics_summary.csv.",
    )
    parser.add_argument(
        "--details-csv",
        default=None,
        help="Per-task detail CSV path. Defaults to <results-parent>/data_analysis_metrics_details.csv.",
    )
    parser.add_argument(
        "--strict-nonempty-final",
        action="store_true",
        help="Treat empty final_answer.txt as not completed for contract-level success.",
    )
    return parser.parse_args()


def normalize(value: str) -> str:
    return " ".join((value or "").strip().split())


def parse_numeric(value: str) -> float | None:
    text = normalize(value)
    if not text:
        return None
    text = text.replace(",", "").replace("$", "").strip()
    multiplier = 1.0
    if text.lower().endswith("k"):
        multiplier = 1000.0
        text = text[:-1].strip()
    if text.endswith("%"):
        text = text[:-1].strip()
    if not re.fullmatch(r"[-+]?\d*\.?\d+", text):
        return None
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def local_match(prediction: str, answer: str) -> bool:
    if prediction == answer:
        return True
    if normalize(prediction) == normalize(answer):
        return True
    pred_value = parse_numeric(prediction)
    answer_value = parse_numeric(answer)
    if pred_value is None or answer_value is None:
        return False
    return math.isclose(pred_value, answer_value, rel_tol=1e-6, abs_tol=1e-6)


def read_jsonl_last(path: Path) -> dict[str, Any] | None:
    try:
        lines = [line for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
    except OSError:
        return None
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def read_metadata(data_root: Path, task_id: str) -> dict[str, Any]:
    metadata_path = data_root / task_id / "metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return {}


def format_metric(value: Any) -> str:
    if value is None:
        return MISSING
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def discover_variant_dirs(results_parent: Path) -> list[Path]:
    variant_dirs = [item for item in sorted(results_parent.iterdir()) if item.is_dir()]
    return [item for item in variant_dirs if list(item.glob("*/*_outputs.jsonl"))]


def evaluate_variant(variant_dir: Path, data_root: Path, task_prefix: str, strict_nonempty_final: bool):
    detail_rows = []
    jsonl_paths = sorted(variant_dir.glob("*/*_outputs.jsonl"))
    if task_prefix:
        jsonl_paths = [path for path in jsonl_paths if path.parent.name.startswith(task_prefix)]

    totals = {
        "tasks": 0,
        "has_answer": 0,
        "matched": 0,
        "artifact_present": 0,
        "nonempty_final": 0,
        "contract_success": 0,
        "exec_success": 0,
        "steps": 0,
        "valid_steps": 0,
    }
    time_values = []
    error_values = []
    variants = set()

    for jsonl_path in jsonl_paths:
        task_id = jsonl_path.parent.name
        record = read_jsonl_last(jsonl_path)
        if record is None:
            continue

        totals["tasks"] += 1
        variants.add(record.get("tame_variant") or (record.get("tame_layers") or {}).get("variant") or variant_dir.name)

        plan = record.get("plan") or []
        step_count = len(plan)
        valid_step_count = sum(1 for item in plan if item.get("is_success"))
        final_exec_success = bool(plan and plan[-1].get("is_success"))
        totals["steps"] += step_count
        totals["valid_steps"] += valid_step_count
        totals["exec_success"] += int(final_exec_success)

        time_cost = record.get("time_cost")
        if isinstance(time_cost, (int, float)):
            time_values.append(float(time_cost))

        error_list = record.get("error_list")
        if isinstance(error_list, list):
            error_values.append(sum(item for item in error_list if isinstance(item, int)))

        output_dir = Path(record.get("output_dir", ""))
        run_dir = output_dir if output_dir.is_absolute() else PROJECT_ROOT / output_dir
        final_path = run_dir / "final_answer.txt"
        artifact_present = final_path.exists()
        prediction = final_path.read_text(encoding="utf-8", errors="ignore").strip() if artifact_present else ""
        nonempty_final = bool(prediction)
        contract_success = artifact_present and (nonempty_final or not strict_nonempty_final)
        totals["artifact_present"] += int(artifact_present)
        totals["nonempty_final"] += int(nonempty_final)
        totals["contract_success"] += int(contract_success)

        metadata = read_metadata(data_root, task_id)
        answer = str(metadata.get("answer", "")).strip()
        has_answer = bool(answer)
        matched = local_match(prediction, answer) if has_answer and artifact_present else False
        totals["has_answer"] += int(has_answer)
        totals["matched"] += int(matched)

        detail_rows.append(
            {
                "variant_dir": variant_dir.name,
                "tame_variant": next(iter(variants)) if len(variants) == 1 else ",".join(sorted(variants)),
                "task_id": task_id,
                "has_answer": has_answer,
                "answer": answer if has_answer else MISSING,
                "prediction": prediction if artifact_present else MISSING,
                "local_match": matched if has_answer else MISSING,
                "artifact_present": artifact_present,
                "nonempty_final": nonempty_final,
                "contract_success": contract_success,
                "exec_success": final_exec_success,
                "step_count": step_count,
                "valid_step_count": valid_step_count,
                "time_cost": time_cost if isinstance(time_cost, (int, float)) else MISSING,
                "output_dir": str(run_dir),
            }
        )

    task_total = totals["tasks"]
    summary = {
        "variant_dir": variant_dir.name,
        "tame_variant": ",".join(sorted(variants)) if variants else variant_dir.name,
        "tasks": task_total,
        "TSR": ratio(totals["matched"], totals["has_answer"]) if totals["has_answer"] else None,
        "TSR_basis": "answer_match" if totals["has_answer"] else MISSING,
        "answer_tasks": totals["has_answer"] if totals["has_answer"] else MISSING,
        "matched_tasks": totals["matched"] if totals["has_answer"] else MISSING,
        "contract_success_rate": ratio(totals["contract_success"], task_total),
        "artifact_present_rate": ratio(totals["artifact_present"], task_total),
        "nonempty_final_rate": ratio(totals["nonempty_final"], task_total),
        "exec_success_rate": ratio(totals["exec_success"], task_total),
        "SC": ratio(totals["steps"], task_total),
        "EVR": ratio(totals["valid_steps"], totals["steps"]),
        "GDR": None,
        "RSR": None,
        "RQR": ratio(totals["contract_success"], task_total),
        "avg_time": mean(time_values) if time_values else None,
        "median_time": median(time_values) if time_values else None,
        "max_time": max(time_values) if time_values else None,
        "avg_error_count": mean(error_values) if error_values else None,
    }
    return summary, detail_rows


def main():
    args = parse_args()
    results_parent = Path(args.results_parent)
    data_root = Path(args.data_root)
    output_csv = Path(args.output_csv) if args.output_csv else results_parent / "data_analysis_metrics_summary.csv"
    details_csv = Path(args.details_csv) if args.details_csv else results_parent / "data_analysis_metrics_details.csv"

    summaries = []
    details = []
    for variant_dir in discover_variant_dirs(results_parent):
        summary, detail_rows = evaluate_variant(
            variant_dir,
            data_root,
            args.task_prefix,
            args.strict_nonempty_final,
        )
        summaries.append(summary)
        details.extend(detail_rows)
        print(
            f"{summary['variant_dir']}: "
            f"tasks={summary['tasks']} "
            f"TSR={format_metric(summary['TSR'])} "
            f"contract={format_metric(summary['contract_success_rate'])} "
            f"artifact={format_metric(summary['artifact_present_rate'])} "
            f"nonempty={format_metric(summary['nonempty_final_rate'])} "
            f"exec={format_metric(summary['exec_success_rate'])} "
            f"SC={format_metric(summary['SC'])} "
            f"EVR={format_metric(summary['EVR'])}"
        )

    summary_fields = [
        "variant_dir",
        "tame_variant",
        "tasks",
        "TSR",
        "TSR_basis",
        "answer_tasks",
        "matched_tasks",
        "contract_success_rate",
        "artifact_present_rate",
        "nonempty_final_rate",
        "exec_success_rate",
        "SC",
        "EVR",
        "GDR",
        "RSR",
        "RQR",
        "avg_time",
        "median_time",
        "max_time",
        "avg_error_count",
    ]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        for row in summaries:
            writer.writerow({field: format_metric(row.get(field)) for field in summary_fields})

    detail_fields = [
        "variant_dir",
        "tame_variant",
        "task_id",
        "has_answer",
        "answer",
        "prediction",
        "local_match",
        "artifact_present",
        "nonempty_final",
        "contract_success",
        "exec_success",
        "step_count",
        "valid_step_count",
        "time_cost",
        "output_dir",
    ]
    details_csv.parent.mkdir(parents=True, exist_ok=True)
    with details_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(details)

    print(f"Saved summary to {output_csv}")
    print(f"Saved details to {details_csv}")


if __name__ == "__main__":
    main()
