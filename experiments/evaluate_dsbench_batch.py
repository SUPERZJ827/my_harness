import argparse
import csv
import json
import math
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(description="Batch-evaluate DSBench result directories under one root")
    parser.add_argument("--results-parent", required=True, help="Parent directory containing variant result folders")
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"))
    parser.add_argument("--task-prefix", default="dsbench_da_")
    parser.add_argument(
        "--output-summary-csv",
        default=None,
        help="Optional summary CSV path. Defaults to <results-parent>/batch_eval_summary.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for per-variant CSV reports. Defaults to <results-parent>/batch_eval_reports",
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


def numeric_match(prediction: str, answer: str) -> bool:
    pred_value = parse_numeric(prediction)
    answer_value = parse_numeric(answer)
    if pred_value is None or answer_value is None:
        return False
    return math.isclose(pred_value, answer_value, rel_tol=1e-6, abs_tol=1e-6)


def select_prediction_file(task_result_dir: Path) -> Path | None:
    if not task_result_dir.exists():
        return None
    run_dirs = [item for item in task_result_dir.iterdir() if item.is_dir()]
    run_dirs.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    for run_dir in run_dirs:
        candidate = run_dir / "final_answer.txt"
        if candidate.exists():
            return candidate
    return None


def evaluate_variant(results_root: Path, data_root: Path, task_prefix: str):
    rows = []
    total = 0
    matched = 0
    completed = 0

    for task_dir in sorted(data_root.iterdir()):
        if not task_dir.is_dir() or not task_dir.name.startswith(task_prefix):
            continue
        metadata_path = task_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        answer = str(metadata.get("answer", "")).strip()

        task_result_dir = results_root / task_dir.name
        prediction_path = select_prediction_file(task_result_dir)
        prediction = prediction_path.read_text(encoding="utf-8").strip() if prediction_path else ""

        exact = prediction == answer
        normalized_exact = normalize(prediction) == normalize(answer)
        numeric_equivalent = numeric_match(prediction, answer)
        local_match = exact or normalized_exact or numeric_equivalent

        total += 1
        completed += int(bool(prediction_path))
        matched += int(local_match)

        rows.append(
            {
                "task_dir": task_dir.name,
                "challenge_id": metadata.get("challenge_id", ""),
                "question_name": metadata.get("question_name", ""),
                "year": metadata.get("year", ""),
                "prediction": prediction,
                "answer": answer,
                "exact_match": exact,
                "normalized_exact_match": normalized_exact,
                "numeric_match": numeric_equivalent,
                "local_match": local_match,
                "prediction_file": str(prediction_path) if prediction_path else "",
            }
        )

    return rows, total, completed, matched


def write_variant_report(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "task_dir",
                "challenge_id",
                "question_name",
                "year",
                "prediction",
                "answer",
                "exact_match",
                "normalized_exact_match",
                "numeric_match",
                "local_match",
                "prediction_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    results_parent = Path(args.results_parent)
    data_root = Path(args.data_root)
    output_dir = Path(args.output_dir) if args.output_dir else results_parent / "batch_eval_reports"
    output_summary_csv = (
        Path(args.output_summary_csv) if args.output_summary_csv else results_parent / "batch_eval_summary.csv"
    )

    variant_dirs = [item for item in sorted(results_parent.iterdir()) if item.is_dir()]
    summary_rows = []

    for variant_dir in variant_dirs:
        rows, total, completed, matched = evaluate_variant(variant_dir, data_root, args.task_prefix)
        report_path = output_dir / f"{variant_dir.name}.csv"
        write_variant_report(report_path, rows)
        accuracy = (matched / total) if total else 0.0
        summary_rows.append(
            {
                "variant_dir": variant_dir.name,
                "total_tasks": total,
                "completed_tasks": completed,
                "local_matched_tasks": matched,
                "local_match_accuracy": f"{accuracy:.4f}",
                "report_csv": str(report_path),
            }
        )
        print(
            f"{variant_dir.name}: completed {completed}/{total}, "
            f"local matched {matched}/{total}, accuracy {accuracy:.4f}"
        )

    output_summary_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variant_dir",
                "total_tasks",
                "completed_tasks",
                "local_matched_tasks",
                "local_match_accuracy",
                "report_csv",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Saved batch summary to {output_summary_csv}")


if __name__ == "__main__":
    main()
