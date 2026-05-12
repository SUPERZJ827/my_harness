import argparse
import csv
import json
import math
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate DSBench pilot outputs produced by DataSciBench")
    parser.add_argument("--results-root", default=str(PROJECT_ROOT / "results"))
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"))
    parser.add_argument("--task-prefix", default="dsbench_da_")
    parser.add_argument("--output-csv", default=str(PROJECT_ROOT / "evaluation_results" / "dsbench_pilot_eval.csv"))
    return parser.parse_args()


def normalize(value: str) -> str:
    return " ".join((value or "").strip().split())


def select_prediction_file(task_result_dir: Path) -> Path | None:
    run_dirs = [item for item in task_result_dir.iterdir() if item.is_dir()]
    run_dirs.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    for run_dir in run_dirs:
        candidate = run_dir / "final_answer.txt"
        if candidate.exists():
            return candidate
    return None


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


def main():
    args = parse_args()
    results_root = Path(args.results_root)
    data_root = Path(args.data_root)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    total = 0
    matched = 0
    completed = 0

    for task_dir in sorted(data_root.iterdir()):
        if not task_dir.is_dir() or not task_dir.name.startswith(args.task_prefix):
            continue
        metadata_path = task_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        answer = str(metadata.get("answer", "")).strip()

        task_result_dir = results_root / task_dir.name
        prediction_path = select_prediction_file(task_result_dir) if task_result_dir.exists() else None
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

    with output_csv.open("w", newline="", encoding="utf-8") as f:
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

    print(f"Evaluated {total} tasks")
    print(f"Completed tasks: {completed}/{total}")
    print(f"Local match accuracy: {(matched / total) if total else 0.0:.4f}")
    print(f"Saved per-task report to {output_csv}")


if __name__ == "__main__":
    main()
