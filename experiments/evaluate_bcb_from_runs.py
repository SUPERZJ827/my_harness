import argparse
import concurrent.futures
import csv
import os
import shutil
from pathlib import Path

from src.utils import load_yaml
from utils.cr_for_bcb import evaluate_cr
from utils.json_operator import read_json
from utils.test_code import test_comp_func, test_gt_func, test_metric_func


def parse_arguments():
    parser = argparse.ArgumentParser(description="Evaluate BCB tasks from run_examples output directories.")
    parser.add_argument("--runs-dir", required=True, help="Directory containing bcb*/ outputs")
    parser.add_argument("--output-csv", required=True, help="Where to write per-task BCB results")
    parser.add_argument("--metric-dir", default="metric", help="Metric root directory")
    return parser.parse_args()


def extract_answer_func(plan: list) -> str:
    ans = ""
    func_defined = False
    for item in plan:
        task_code = item.get("code", "")
        if "def task_func" in task_code:
            if func_defined and "return" in ans.split("def task_func", 1)[1]:
                break
            func_defined = True
        ans += "\n" + task_code
        lines = task_code.strip().splitlines()
        if lines and "return" in lines[-1] and func_defined:
            break
    return ans


def first_output_jsonl(task_dir: Path) -> Path | None:
    files = sorted(task_dir.glob("*_outputs.jsonl"))
    return files[0] if files else None


def evaluate_one(task_id: str, output_file: Path, metric_file: Path) -> dict:
    metric_config = load_yaml(str(metric_file))
    output_datas = read_json(str(output_file))
    if not output_datas:
        return {"task_id": task_id, "cr": 0.0, "pass": 0, "tmc_mean": None, "time_cost": 0.0, "error": "empty output"}

    cur_data = output_datas[0]
    cur_answer = extract_answer_func(cur_data.get("plan", []))
    row = {
        "task_id": task_id,
        "cr": 0.0,
        "pass": 0,
        "tmc_mean": None,
        "time_cost": float(cur_data.get("time_cost", 0.0) or 0.0),
        "error": "",
    }
    abs_dir = os.getcwd()
    try:
        temp_dict = {}
        exec(metric_config["data"], locals())
        if "pip" in cur_answer or "os.system" in cur_answer:
            raise RuntimeError("Pip or os.system is not allowed")
        if cur_answer.count("def task_func") > 2:
            raise RuntimeError("Multiple task_func definitions are not allowed")
        exec(cur_answer, locals())
        with concurrent.futures.ThreadPoolExecutor() as executor:
            exec(test_comp_func, locals(), temp_dict)
        exec(metric_config["ground_truth"], locals())
        exec(test_gt_func, locals(), temp_dict)
        cr_value = float(evaluate_cr(temp_dict["cur_completion_output"], temp_dict["gt_output"]))
        row["cr"] = cr_value
        row["pass"] = int(cr_value >= 1.0)

        tmc_values = []
        for tmc in metric_config.get("TMC-list", []):
            func_code = tmc["code"]
            metric_func_name = func_code.split("def", 1)[1].split("(", 1)[0].strip()
            metric_scope = dict(temp_dict)
            try:
                exec(func_code, locals(), metric_scope)
                exec(test_metric_func.format(metric_func_name=metric_func_name), locals(), metric_scope)
                metric_output = metric_scope.get("metric_output")
                if metric_output is not None:
                    tmc_values.append(float(metric_output))
            except Exception:
                tmc_values.append(0.0)
        if tmc_values:
            row["tmc_mean"] = sum(tmc_values) / len(tmc_values)
    except Exception as exc:
        row["error"] = repr(exc)
    finally:
        os.chdir(abs_dir)
        if os.path.exists("data/task_func"):
            shutil.rmtree("data/task_func")
    return row


def main():
    args = parse_arguments()
    runs_dir = Path(args.runs_dir)
    metric_dir = Path(args.metric_dir)
    rows = []
    for task_dir in sorted(runs_dir.glob("bcb*")):
        if not task_dir.is_dir():
            continue
        metric_file = metric_dir / task_dir.name / "metric.yaml"
        output_file = first_output_jsonl(task_dir)
        if not metric_file.exists() or output_file is None:
            rows.append({"task_id": task_dir.name, "cr": 0.0, "pass": 0, "tmc_mean": None, "time_cost": 0.0, "error": "missing metric or output"})
            continue
        rows.append(evaluate_one(task_dir.name, output_file, metric_file))

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["task_id", "cr", "pass", "tmc_mean", "time_cost", "error"])
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    avg_cr = sum(float(row["cr"]) for row in rows) / total if total else 0.0
    pass_at_1 = sum(int(row["pass"]) for row in rows) / total if total else 0.0
    print(f"BCB tasks: {total}")
    print(f"Average CR: {avg_cr:.4f}")
    print(f"Pass@1: {pass_at_1:.4f}")
    print(f"Saved: {output_csv}")


if __name__ == "__main__":
    main()
