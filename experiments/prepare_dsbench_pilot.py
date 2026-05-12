import argparse
import json
import shutil
from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_TASKSET_FILE = PROJECT_ROOT / "experiments" / "dsbench_task_sets.json"
DEFAULT_DSBENCH_ROOT = Path("/home/zhoujun/DSBench")

PROMPT_TEMPLATE = """Answer the following DSBench data-analysis task using only the files staged in the current directory.

Challenge ID: {challenge_id}
Challenge Name: {challenge_name}
Year: {year}
Question ID: {question_name}

Challenge Background:
{introduction}

Current Question:
{question}

Available support files in the current directory:
{support_files}

Required output:
1. Write the final answer only to a UTF-8 text file named `final_answer.txt`.
2. The content of `final_answer.txt` must contain only the final answer string and nothing else.
3. Use the workbook / image / csv files staged in `./` as needed. Read inputs from `./` and write outputs to `./`.
4. If the question is multiple choice, write only the final choice exactly as the answer format requires.
5. Do not write explanations into `final_answer.txt`.

DSBench workbook-solving requirements:
1. Treat each task as a spreadsheet/data-analysis problem. Do not answer from memory or from the question text alone.
2. Before computing the final answer, inspect the staged workbook files with `openpyxl` and/or `pandas`: list sheet names, sheet dimensions, visible data ranges, and relevant formulas or cell values.
3. If an image file such as a flow chart is staged, use it as task context when the question or introduction references it. Do not ignore image files that are listed as support files.
4. For multiple-choice questions, read the option list from the question text, compute the underlying value or condition, then map the result to exactly one option letter.
5. For free-field questions, write the requested value or name in the format requested by the question; do not write a placeholder, debug string, or explanation.
6. Do not write `Not Applicable` merely because workbook parsing is difficult. Use `Not Applicable` only after confirming that the required workbook/question/support files or requested entity are genuinely absent.
7. If a workbook contains formulas, inspect both formula cells and cached/displayed values where available. Do not assume `pandas.read_excel` alone captures the full workbook logic.
{extra_instructions}
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare a DSBench data-analysis pilot as DataSciBench task folders")
    parser.add_argument("--dsbench-root", default=str(DEFAULT_DSBENCH_ROOT), help="Local DSBench repository path")
    parser.add_argument(
        "--source-zip",
        default=None,
        help="Optional explicit path to DSBench data_analysis zip. Defaults to <dsbench-root>/data_analysis/data_old.zip",
    )
    parser.add_argument(
        "--meta-file",
        default=None,
        help="Optional explicit path to DSBench data_analysis/data.json. Defaults to <dsbench-root>/data_analysis/data.json",
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of per-question tasks to prepare")
    parser.add_argument("--start", type=int, default=0, help="Starting question offset in the flattened DSBench question list")
    parser.add_argument("--year", type=int, default=None, help="Optional year filter")
    parser.add_argument("--output-data-dir", default=str(DEFAULT_OUTPUT_DATA_DIR))
    parser.add_argument("--taskset-file", default=str(DEFAULT_TASKSET_FILE))
    parser.add_argument("--task-prefix", default="dsbench_da")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def answer_to_text(answer):
    if isinstance(answer, (dict, list)):
        return json.dumps(answer, ensure_ascii=False, sort_keys=True)
    return str(answer)


def sanitize_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in value)


def is_multiple_choice_answer(answer) -> bool:
    text = answer_to_text(answer).strip()
    return len(text) == 1 and text.isalpha()


def build_prompt(
    sample: dict,
    question_name: str,
    introduction: str,
    question: str,
    support_files: list[str],
    answer,
) -> str:
    support_block = "\n".join(f"- {name}" for name in support_files) if support_files else "- (none)"
    extra_instructions = ""
    if is_multiple_choice_answer(answer):
        extra_instructions = (
            "\n6. This task is a multiple-choice question.\n"
            "7. First compute the underlying result internally, then map that result to exactly one option letter from the question.\n"
            "8. Do not write any intermediate numeric value, percentage, currency amount, team name, free-text answer, or explanation to `final_answer.txt`.\n"
            "9. For this task, `final_answer.txt` must contain exactly one uppercase option letter such as `A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`, or `I`.\n"
            "10. If you compute a value such as `728050`, `$34,274,780`, or `123.4%`, do not write that value to `final_answer.txt`; write only its corresponding option letter.\n"
            "11. If `final_answer.txt` contains anything other than one uppercase option letter, the answer is invalid."
        )
    return PROMPT_TEMPLATE.format(
        challenge_id=sample["id"],
        challenge_name=sample["name"],
        year=sample.get("year", ""),
        question_name=question_name,
        introduction=introduction.strip(),
        question=question.strip(),
        support_files=support_block,
        extra_instructions=extra_instructions,
    )


def main():
    args = parse_args()
    dsbench_root = Path(args.dsbench_root)
    source_zip = Path(args.source_zip) if args.source_zip else dsbench_root / "data_analysis" / "data_old.zip"
    meta_file = Path(args.meta_file) if args.meta_file else dsbench_root / "data_analysis" / "data.json"
    output_data_dir = Path(args.output_data_dir)
    taskset_file = Path(args.taskset_file)

    if not source_zip.exists():
        raise FileNotFoundError(f"DSBench source zip not found: {source_zip}")
    if not meta_file.exists():
        raise FileNotFoundError(f"DSBench metadata file not found: {meta_file}")

    samples = [json.loads(line) for line in meta_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.year is not None:
        samples = [sample for sample in samples if sample.get("year") == args.year]

    flattened = []
    for sample in samples:
        for question_name, answer in zip(sample["questions"], sample["answers"]):
            flattened.append(
                {
                    "sample": sample,
                    "question_name": question_name,
                    "answer": answer,
                }
            )

    selected = flattened[args.start : args.start + args.limit]
    if not selected:
        raise ValueError("No DSBench questions matched the requested range/filter")

    created_task_ids = []
    with ZipFile(source_zip) as zf:
        names = set(zf.namelist())
        for item in selected:
            sample = item["sample"]
            question_name = item["question_name"]
            answer = item["answer"]
            challenge_dir = f"data/{sample['id']}/"
            intro_name = f"{challenge_dir}introduction.txt"
            question_file_name = f"{challenge_dir}{question_name}.txt"
            if intro_name not in names:
                raise FileNotFoundError(f"Missing {intro_name} in {source_zip}")
            if question_file_name not in names:
                raise FileNotFoundError(f"Missing {question_file_name} in {source_zip}")

            introduction = zf.read(intro_name).decode("utf-8", errors="ignore")
            question = zf.read(question_file_name).decode("utf-8", errors="ignore")

            support_members = []
            for member in sorted(names):
                if not member.startswith(challenge_dir):
                    continue
                basename = member.split("/")[-1]
                if not basename or basename.startswith("._") or basename == ".DS_Store":
                    continue
                if basename == "introduction.txt" or basename == f"{question_name}.txt":
                    continue
                if basename.startswith("question") and basename.endswith(".txt"):
                    continue
                support_members.append(member)

            task_name = f"{args.task_prefix}_{sample['id']}_{sanitize_name(question_name)}"
            task_dir = output_data_dir / task_name
            if task_dir.exists():
                if not args.overwrite:
                    raise FileExistsError(f"{task_dir} already exists; rerun with --overwrite to replace it")
                shutil.rmtree(task_dir)
            task_dir.mkdir(parents=True, exist_ok=True)

            for member in support_members:
                target = task_dir / Path(member).name
                with zf.open(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

            (task_dir / "introduction.txt").write_text(introduction, encoding="utf-8")
            (task_dir / f"{question_name}.txt").write_text(question, encoding="utf-8")

            support_file_names = [Path(member).name for member in support_members]
            support_file_names.extend(["introduction.txt", f"{question_name}.txt"])

            prompt_payload = {
                "prompt": build_prompt(
                    sample,
                    question_name,
                    introduction,
                    question,
                    sorted(support_file_names),
                    answer,
                ),
                "data_source_type": "2=open source data",
            }
            metadata_payload = {
                "benchmark": "DSBench",
                "benchmark_track": "data_analysis",
                "challenge_id": sample["id"],
                "challenge_name": sample["name"],
                "question_name": question_name,
                "question": question,
                "introduction": introduction,
                "answer": answer_to_text(answer),
                "answer_raw": answer,
                "answer_format": "multiple_choice_letter" if is_multiple_choice_answer(answer) else "open_answer",
                "year": sample.get("year", ""),
                "source_zip": str(source_zip),
            }

            (task_dir / "prompt.json").write_text(json.dumps(prompt_payload, ensure_ascii=False), encoding="utf-8")
            (task_dir / "metadata.json").write_text(
                json.dumps(metadata_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            created_task_ids.append(task_name)

    taskset_file.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        f"{args.task_prefix}_pilot_{len(created_task_ids)}": created_task_ids,
    }
    taskset_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Prepared {len(created_task_ids)} DSBench data-analysis tasks")
    print(f"Task set manifest: {taskset_file}")
    print(f"Task ids: {created_task_ids}")


if __name__ == "__main__":
    main()
