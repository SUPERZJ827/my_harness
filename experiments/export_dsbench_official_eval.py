import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DSBENCH_ROOT = Path("/home/zhoujun/DSBench")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export DataSciBench DSBench results into a DSBench-official evaluation workspace"
    )
    parser.add_argument("--results-root", required=True, help="DataSciBench DSBench results root")
    parser.add_argument("--dsbench-root", default=str(DEFAULT_DSBENCH_ROOT), help="Local DSBench repository path")
    parser.add_argument(
        "--source-zip",
        default=None,
        help="Optional explicit DSBench data zip path. Defaults to <dsbench-root>/data_analysis/data_old.zip",
    )
    parser.add_argument(
        "--meta-file",
        default=None,
        help="Optional explicit DSBench data_analysis/data.json path. Defaults to <dsbench-root>/data_analysis/data.json",
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "dsbench_official_eval"),
        help="Where to create the isolated official-eval workspace",
    )
    parser.add_argument(
        "--eval-label",
        default=None,
        help="Label under save_process/. Defaults to the basename of results-root",
    )
    parser.add_argument("--task-prefix", default="dsbench_da_")
    parser.add_argument(
        "--workspace-name",
        default=None,
        help="Workspace directory name. Defaults to the basename of results-root",
    )
    parser.add_argument(
        "--openai-api-key",
        default=None,
        help="Optional key used to run the official LLM-judge script immediately",
    )
    parser.add_argument(
        "--judge-model",
        default="gpt-4o-2024-05-13",
        help="Judge model to inject into the copied compute_answer.py",
    )
    parser.add_argument(
        "--run-official-judge",
        action="store_true",
        help="Run copied compute_answer.py and show_result.py after exporting the workspace",
    )
    return parser.parse_args()


def load_dsbench_samples(meta_file: Path):
    return [json.loads(line) for line in meta_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def select_prediction_file(task_result_dir: Path) -> Path | None:
    run_dirs = [item for item in task_result_dir.iterdir() if item.is_dir()]
    run_dirs.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    for run_dir in run_dirs:
        candidate = run_dir / "final_answer.txt"
        if candidate.exists():
            return candidate
    return None


def select_output_manifest(task_result_dir: Path) -> Path | None:
    candidates = sorted(task_result_dir.glob("*outputs.jsonl"))
    return candidates[-1] if candidates else None


def load_manifest_row(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return {}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {}


def extract_relevant_files(source_zip: Path, included_questions: dict[str, set[str]], target_data_dir: Path):
    with ZipFile(source_zip) as zf:
        members = set(zf.namelist())
        for challenge_id, question_names in included_questions.items():
            challenge_dir = target_data_dir / challenge_id
            challenge_dir.mkdir(parents=True, exist_ok=True)
            intro_member = f"data/{challenge_id}/introduction.txt"
            if intro_member in members:
                challenge_dir.joinpath("introduction.txt").write_bytes(zf.read(intro_member))
            for question_name in sorted(question_names):
                member = f"data/{challenge_id}/{question_name}.txt"
                if member not in members:
                    raise FileNotFoundError(f"Missing {member} in {source_zip}")
                challenge_dir.joinpath(f"{question_name}.txt").write_bytes(zf.read(member))


def build_filtered_samples(samples: list[dict], included_questions: dict[str, set[str]]):
    filtered = []
    for sample in samples:
        challenge_id = sample["id"]
        if challenge_id not in included_questions:
            continue
        keep = included_questions[challenge_id]
        pairs = [
            (question_name, answer)
            for question_name, answer in zip(sample["questions"], sample["answers"])
            if question_name in keep
        ]
        if not pairs:
            continue
        filtered_sample = dict(sample)
        filtered_sample["questions"] = [question_name for question_name, _ in pairs]
        filtered_sample["answers"] = [answer for _, answer in pairs]
        filtered.append(filtered_sample)
    return filtered


def write_prediction_files(
    filtered_samples: list[dict],
    records_by_key: dict[tuple[str, str], dict],
    save_process_dir: Path,
):
    save_process_dir.mkdir(parents=True, exist_ok=True)
    for sample in filtered_samples:
        challenge_id = sample["id"]
        output_path = save_process_dir / f"{challenge_id}.json"
        with output_path.open("w", encoding="utf-8") as f:
            for question_name in sample["questions"]:
                record = records_by_key.get((challenge_id, question_name), {})
                payload = {
                    "response": record.get("prediction", ""),
                    "cost": record.get("cost", 0),
                    "time": record.get("time", 0),
                }
                json.dump(payload, f, ensure_ascii=False)
                f.write("\n")


def copy_and_patch_official_scripts(dsbench_root: Path, workspace_dir: Path, eval_label: str, judge_model: str):
    source_dir = dsbench_root / "data_analysis"
    compute_src = source_dir / "compute_answer.py"
    show_src = source_dir / "show_result.py"
    compute_dst = workspace_dir / "compute_answer.py"
    show_dst = workspace_dir / "show_result.py"

    compute_text = compute_src.read_text(encoding="utf-8")
    show_text = show_src.read_text(encoding="utf-8")

    compute_text = "import os\n" + compute_text
    compute_text = compute_text.replace(
        'client = OpenAI(api_key="")',
        'client = OpenAI(api_key=os.environ.get("OPENROUTER_API_KEY", ""), base_url="https://openrouter.ai/api/v1")',
    )
    compute_text = re.sub(r"(?m)^model\s*=\s*['\"][^'\"]+['\"]", f"model = {eval_label!r}", compute_text)
    compute_text = compute_text.replace(
        'model="gpt-4o-2024-05-13"',
        f'model=os.environ.get("OPENROUTER_JUDGE_MODEL", {judge_model!r})',
    )

    show_text = re.sub(r"(?m)^model\s*=\s*['\"][^'\"]+['\"]", f"model = {eval_label!r}", show_text)

    compute_dst.write_text(compute_text, encoding="utf-8")
    show_dst.write_text(show_text, encoding="utf-8")


def main():
    args = parse_args()
    results_root = Path(args.results_root)
    dsbench_root = Path(args.dsbench_root)
    source_zip = Path(args.source_zip) if args.source_zip else dsbench_root / "data_analysis" / "data_old.zip"
    meta_file = Path(args.meta_file) if args.meta_file else dsbench_root / "data_analysis" / "data.json"
    output_root = Path(args.output_root)
    eval_label = args.eval_label or results_root.name
    workspace_name = args.workspace_name or results_root.name
    workspace_dir = output_root / workspace_name / "data_analysis"
    save_process_dir = workspace_dir / "save_process" / eval_label

    if not results_root.exists():
        raise FileNotFoundError(f"Results root not found: {results_root}")
    if not source_zip.exists():
        raise FileNotFoundError(f"DSBench source zip not found: {source_zip}")
    if not meta_file.exists():
        raise FileNotFoundError(f"DSBench metadata file not found: {meta_file}")

    if workspace_dir.parent.exists():
        shutil.rmtree(workspace_dir.parent)
    save_process_dir.mkdir(parents=True, exist_ok=True)

    samples = load_dsbench_samples(meta_file)
    included_questions: dict[str, set[str]] = {}
    records_by_key: dict[tuple[str, str], dict] = {}

    for task_dir in sorted(results_root.iterdir()):
        if not task_dir.is_dir() or not task_dir.name.startswith(args.task_prefix):
            continue
        run_dirs = [item for item in task_dir.iterdir() if item.is_dir()]
        if not run_dirs:
            continue
        latest_run_dir = max(run_dirs, key=lambda item: item.stat().st_mtime)
        metadata_path = latest_run_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        challenge_id = metadata["challenge_id"]
        question_name = metadata["question_name"]

        prediction_path = select_prediction_file(task_dir)
        prediction = prediction_path.read_text(encoding="utf-8").strip() if prediction_path else ""

        manifest = load_manifest_row(select_output_manifest(task_dir))
        cost_value = manifest.get("cost", 0)
        if isinstance(cost_value, list):
            cost_value = cost_value[2] if len(cost_value) >= 3 else 0
        elif isinstance(cost_value, dict):
            cost_value = cost_value.get("total_cost", 0)

        records_by_key[(challenge_id, question_name)] = {
            "prediction": prediction,
            "cost": cost_value or 0,
            "time": manifest.get("time_cost", 0) or 0,
        }
        included_questions.setdefault(challenge_id, set()).add(question_name)

    filtered_samples = build_filtered_samples(samples, included_questions)
    if not filtered_samples:
        raise ValueError(f"No DSBench task records found under {results_root}")

    (workspace_dir / "data").mkdir(parents=True, exist_ok=True)
    extract_relevant_files(source_zip, included_questions, workspace_dir / "data")
    (workspace_dir / "data.json").write_text(
        "\n".join(json.dumps(sample, ensure_ascii=False) for sample in filtered_samples) + "\n",
        encoding="utf-8",
    )
    write_prediction_files(filtered_samples, records_by_key, save_process_dir)
    copy_and_patch_official_scripts(dsbench_root, workspace_dir, eval_label, args.judge_model)

    print(f"Created official-eval workspace: {workspace_dir}")
    print(f"Evaluation label: {eval_label}")
    print(f"Included challenges: {[sample['id'] for sample in filtered_samples]}")
    print(f"Prediction files written under: {save_process_dir}")

    if args.run_official_judge:
        env = os.environ.copy()
        if args.openai_api_key:
            env["OPENROUTER_API_KEY"] = args.openai_api_key
        if "OPENROUTER_API_KEY" not in env or not env["OPENROUTER_API_KEY"]:
            raise ValueError("OPENROUTER_API_KEY is required to run the official judge")
        subprocess.run(["python", "compute_answer.py"], cwd=workspace_dir, check=True, env=env)
        subprocess.run(["python", "show_result.py"], cwd=workspace_dir, check=True, env=env)


if __name__ == "__main__":
    import os

    main()
