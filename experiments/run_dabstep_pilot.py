import argparse
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKSET_FILE = PROJECT_ROOT / "experiments" / "dabstep_task_sets.json"


def parse_args():
    parser = argparse.ArgumentParser(description="Run a prepared DABstep pilot through run_examples.py")
    parser.add_argument(
        "--taskset-file",
        default=str(DEFAULT_TASKSET_FILE),
        help="JSON manifest produced by prepare_dabstep_pilot.py",
    )
    parser.add_argument(
        "--taskset-name",
        default=None,
        help="Manifest key to run. Defaults to the first key in the taskset file.",
    )
    parser.add_argument("--python-bin", default=str(PROJECT_ROOT / "harness" / "bin" / "python"))
    parser.add_argument("--tame-variant", default="minimal_baseline")
    parser.add_argument("--max-runs", type=int, default=1)
    parser.add_argument("--output-dir", default="results_dabstep_minimal")
    parser.add_argument("--data-type", default="all")
    parser.add_argument("--config", default="config2.yaml")
    parser.add_argument("--continue-gen", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    taskset_path = Path(args.taskset_file)
    manifest = json.loads(taskset_path.read_text(encoding="utf-8"))
    if not manifest:
        raise ValueError(f"No task sets found in {taskset_path}")

    taskset_name = args.taskset_name or next(iter(manifest))
    if taskset_name not in manifest:
        available = ", ".join(manifest)
        raise KeyError(f"Task set '{taskset_name}' not found. Available: {available}")

    task_ids = manifest[taskset_name]
    task_ids_literal = json.dumps(task_ids, ensure_ascii=False)
    cmd = [
        args.python_bin,
        "-m",
        "experiments.run_examples",
        "--task_id",
        task_ids_literal,
        "--tame_variant",
        args.tame_variant,
        "--max_runs",
        str(args.max_runs),
        "--output_dir",
        args.output_dir,
        "--data_type",
        args.data_type,
        "--config",
        args.config,
    ]
    if args.continue_gen:
        cmd.append("--continue_gen")

    print(f"Running task set: {taskset_name}")
    print(f"Task count: {len(task_ids)}")
    print("Command:")
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


if __name__ == "__main__":
    main()
