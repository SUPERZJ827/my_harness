import argparse
import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate DABstep pilot outputs produced by DataSciBench")
    parser.add_argument("--results-root", default=str(PROJECT_ROOT / "results"), help="Result root passed to run_examples.py")
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"), help="Task data root")
    parser.add_argument("--task-prefix", default="dabstep_", help="Only evaluate task folders with this prefix")
    parser.add_argument("--output-csv", default=str(PROJECT_ROOT / "evaluation_results" / "dabstep_pilot_eval.csv"))
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


def main():
    args = parse_args()
    results_root = Path(args.results_root)
    data_root = Path(args.data_root)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    correct = 0
    total = 0

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
        total += 1
        correct += int(exact)

        rows.append(
            {
                "task_dir": task_dir.name,
                "task_id": metadata.get("task_id", ""),
                "level": metadata.get("level", ""),
                "prediction": prediction,
                "answer": answer,
                "exact_match": exact,
                "normalized_exact_match": normalized_exact,
                "prediction_file": str(prediction_path) if prediction_path else "",
            }
        )

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "task_dir",
                "task_id",
                "level",
                "prediction",
                "answer",
                "exact_match",
                "normalized_exact_match",
                "prediction_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    accuracy = correct / total if total else 0.0
    print(f"Evaluated {total} tasks")
    print(f"Exact match accuracy: {accuracy:.4f}")
    print(f"Saved per-task report to {output_csv}")


if __name__ == "__main__":
    main()
