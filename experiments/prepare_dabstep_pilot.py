import argparse
import json
import shutil
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import snapshot_download


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_CONTEXT_CACHE_DIR = PROJECT_ROOT / "hf_dataset_tmp" / "dabstep"
DEFAULT_TASKSET_FILE = PROJECT_ROOT / "experiments" / "dabstep_task_sets.json"

PROMPT_TEMPLATE = """Answer the following DABstep task using only the files staged in the current directory.

Task ID: {task_id}
Difficulty: {level}

Question:
{question}

Answer formatting guidelines:
{guidelines}

Available context files in the current directory:
- payments.csv
- fees.json
- manual.md
- merchant_data.json
- merchant_category_codes.csv
- acquirer_countries.csv
- payments-readme.md

DABstep schema and execution hints:
1. Inspect the real input files before writing the final computation. Do not invent column names or JSON keys.
2. For `payments.csv`, important columns include:
   - `merchant`: merchant name string. Do not assume a `merchant_id` column exists.
   - `ip_country`: shopper IP country.
   - `issuing_country`: card issuing country.
   - `eur_amount`: transaction amount in EUR.
   - `shopper_interaction`: payment channel. `Ecommerce` means ecommerce and `POS` means in-store.
   - `has_fraudulent_dispute`: boolean fraud indicator. Do not use non-existent columns such as `is_fraud`.
   - `is_refused_by_adyen`: boolean refusal indicator.
   - `card_scheme`, `is_credit`, `aci`, `acquirer_country`, `year`, `day_of_year`, `hour_of_day`.
3. For `merchant_data.json`, merchant records use the key `merchant` for the merchant name, plus keys such as `capture_delay`, `acquirer`, `merchant_category_code`, and `account_type`.
4. `fees.json` is a list of fee-rule records, not a top-level dictionary. Iterate over the list or inspect the first record before using it. Do not call `.get(...)` on the top-level `fees` object unless you have verified it is a dictionary.
5. For fee questions, read `fees.json` and `manual.md`; do not infer fee thresholds from memory.
6. For country mapping questions, use the country code values exactly as they appear in the files.
7. If a question asks for the top country "for fraud", compare countries by fraud rate/proportion unless the wording explicitly asks for raw fraud count.
8. If a requested entity or condition is not present in the staged files after checking the relevant files, the correct output is `Not Applicable`.

Robustness requirements:
1. Before accessing a column, check that it exists in the loaded DataFrame.
2. Before accessing a JSON key, inspect at least one record or use safe dictionary access.
3. Before opening an optional context file such as `manual.md` or `payments-readme.md`, check whether it exists. If it is absent, continue using the available files.
4. Avoid crashing before writing `final_answer.txt`. If the task is genuinely not applicable, write exactly `Not Applicable`.
5. Do not write explanations, debug output, code fences, or extra whitespace into `final_answer.txt`.
6. If the answer formatting guideline asks for a multiple-choice answer like `A. NL`, write exactly the chosen option in that format, not only the computed value.

Required output:
1. Write the final answer only to a UTF-8 text file named `final_answer.txt`.
2. The content of `final_answer.txt` must contain only the final answer string and nothing else.
3. You may create temporary analysis files if needed, but `final_answer.txt` is the only required deliverable.
4. If the question does not have an applicable answer, write exactly `Not Applicable`.
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare a DABstep pilot as DataSciBench-compatible task folders")
    parser.add_argument("--dataset", default="adyen/DABstep", help="Hugging Face dataset id")
    parser.add_argument("--subset", default="tasks", help="Dataset subset name")
    parser.add_argument("--split", default="dev", help="Dataset split name")
    parser.add_argument("--limit", type=int, default=10, help="Number of tasks to prepare")
    parser.add_argument("--level", default="all", choices=["easy", "hard", "all"], help="Difficulty filter")
    parser.add_argument(
        "--output-data-dir",
        default=str(DEFAULT_OUTPUT_DATA_DIR),
        help="Directory where dabstep_* task folders will be created",
    )
    parser.add_argument(
        "--context-cache-dir",
        default=str(DEFAULT_CONTEXT_CACHE_DIR),
        help="Directory where the shared DABstep context files will be downloaded",
    )
    parser.add_argument(
        "--task-prefix",
        default="dabstep",
        help="Task folder prefix. A task id 123 becomes <prefix>_123",
    )
    parser.add_argument(
        "--taskset-file",
        default=str(DEFAULT_TASKSET_FILE),
        help="Where to write the generated pilot task set manifest",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing dabstep_* task folders if they already exist",
    )
    return parser.parse_args()


def ensure_context_files(dataset_id: str, context_cache_dir: Path) -> Path:
    cached_context_dir = context_cache_dir / "data" / "context"
    if cached_context_dir.exists():
        return cached_context_dir

    snapshot_path = snapshot_download(
        repo_id=dataset_id,
        repo_type="dataset",
        allow_patterns=["data/context/*"],
        local_dir=str(context_cache_dir),
        local_dir_use_symlinks=False,
    )
    context_dir = Path(snapshot_path) / "data" / "context"
    if not context_dir.exists():
        raise FileNotFoundError(f"Expected DABstep context files under {context_dir}")
    return context_dir


def build_prompt(row: dict) -> str:
    return PROMPT_TEMPLATE.format(
        task_id=row["task_id"],
        level=row.get("level", "unknown"),
        question=row["question"].strip(),
        guidelines=row["guidelines"].strip(),
    )


def main():
    args = parse_args()
    output_data_dir = Path(args.output_data_dir)
    context_cache_dir = Path(args.context_cache_dir)
    taskset_file = Path(args.taskset_file)

    ds = load_dataset(args.dataset, name=args.subset, split=args.split)
    rows = list(ds)
    if args.level != "all":
        rows = [row for row in rows if row.get("level") == args.level]
    rows = rows[: args.limit]
    if not rows:
        raise ValueError("No DABstep tasks matched the requested filter")

    context_dir = ensure_context_files(args.dataset, context_cache_dir)
    created_task_ids = []

    for row in rows:
        folder_name = f"{args.task_prefix}_{row['task_id']}"
        task_dir = output_data_dir / folder_name
        if task_dir.exists():
            if not args.overwrite:
                raise FileExistsError(f"{task_dir} already exists; rerun with --overwrite to replace it")
            shutil.rmtree(task_dir)
        task_dir.mkdir(parents=True, exist_ok=True)

        for source in context_dir.iterdir():
            if source.is_file():
                shutil.copy2(source, task_dir / source.name)

        prompt_payload = {
            "prompt": build_prompt(row),
            "data_source_type": "2=open source data",
        }
        metadata_payload = {
            "task_id": row["task_id"],
            "question": row["question"],
            "guidelines": row["guidelines"],
            "answer": row.get("answer", ""),
            "level": row.get("level", ""),
            "source_dataset": args.dataset,
            "source_subset": args.subset,
            "source_split": args.split,
        }

        (task_dir / "prompt.json").write_text(json.dumps(prompt_payload, ensure_ascii=False), encoding="utf-8")
        (task_dir / "metadata.json").write_text(json.dumps(metadata_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        created_task_ids.append(folder_name)

    taskset_file.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        f"{args.task_prefix}_pilot_{len(created_task_ids)}": created_task_ids,
    }
    taskset_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Prepared {len(created_task_ids)} DABstep tasks")
    print(f"Task set manifest: {taskset_file}")
    print(f"Task ids: {created_task_ids}")


if __name__ == "__main__":
    main()
