import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_METAGPT_ROOT = PROJECT_ROOT / "MetaGPT"
if str(LOCAL_METAGPT_ROOT) not in sys.path:
    sys.path.insert(0, str(LOCAL_METAGPT_ROOT))

from dataclasses import asdict
# from metagpt.roles.di.data_interpreter import DataInterpreter
from role import SciDataInterpreter
from src.logs import create_logger, get_model_name, resolve_config_path
from metagpt.logs import logger
import os
from src.utils import change_dir, change_metalog_path
import argparse
import time
import json
import shutil
import csv
from src.schemas import SciAgentBenchOutput
from metagpt.config2 import Config
from role.tame_config import TAMEConfig, TAMEVariant, tame_contract_prompt
from role.tame_artifacts import build_artifact_contract
from experiments.dsbench_adapter import (
    dsbench_adapter_prompt,
    ensure_adapter_files,
    is_dsbench_task,
    normalize_final_answer,
)

SPECIFY_PATH_PROMPT = "All input source data has been staged into the current folder `./`. Read inputs from `./` and save all output files to `./`.\n\n"

BCB_OUTPUT_PROMPT = "Complete the following instructions and write the final python code in a file named `output.py` using with open(...)\n\n"

INPUT_SUFFIXES = {
    ".csv",
    ".xlsx",
    ".xls",
    ".json",
    ".md",
    ".parquet",
    ".txt",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
    ".npy",
    ".pkl",
    ".h5",
    ".pth",
    ".data",
    ".test",
}
INPUT_DIR_ALLOWLIST = {".data", "data", "heart+disease"}
CSV_EXCEL_48_COLUMNS = [
    "Age",
    "Occupation",
    "Family Income",
    "Education",
    "Marital Status",
    "Job Type",
    "Family Size",
    "Ethnicity",
    "Gender",
    "Workplace",
    "Label",
]
CSV_EXCEL_48_NOTE = (
    "\n\nDataset header note: the staged CSV files have 11 columns: "
    + ", ".join(CSV_EXCEL_48_COLUMNS)
    + ". Use Label as the target column; Workplace is an input feature.\n"
)

TASKSETS = {
    "original_55": [
        "csv_excel_0",
        "csv_excel_1",
        "csv_excel_10",
        "csv_excel_11",
        "csv_excel_2",
        "csv_excel_29",
        "csv_excel_3",
        "csv_excel_30",
        "csv_excel_32",
        "csv_excel_33",
        "csv_excel_34",
        "csv_excel_37",
        "csv_excel_39",
        "csv_excel_4",
        "csv_excel_41",
        "csv_excel_46",
        "csv_excel_47",
        "csv_excel_48",
        "csv_excel_8",
        "csv_excel_9",
        "dl_0",
        "dl_1",
        "dl_10",
        "dl_13",
        "dl_15",
        "dl_16",
        "dl_30",
        "dl_31",
        "dl_6",
        "dl_9",
        "human_0",
        "human_1",
        "human_10",
        "human_11",
        "human_12",
        "human_131",
        "human_132",
        "human_141",
        "human_142",
        "human_15",
        "human_16",
        "human_17",
        "human_18",
        "human_19",
        "human_2",
        "human_20",
        "human_21",
        "human_22",
        "human_23",
        "human_24",
        "human_3",
        "human_5",
        "human_7",
        "human_8",
        "human_9",
    ],
}


def normalize_csv_excel_48_headers(run_dir: str):
    for file_name in ("Bayesian_Dataset_train.csv", "Bayesian_Dataset_test.csv"):
        path = os.path.join(run_dir, file_name)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        if not rows or len(rows[0]) != len(CSV_EXCEL_48_COLUMNS):
            continue
        if rows[0] == CSV_EXCEL_48_COLUMNS:
            continue
        rows[0] = CSV_EXCEL_48_COLUMNS
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)


def stage_task_inputs(task_dir: str, run_dir: str):
    for name in os.listdir(task_dir):
        src = os.path.join(task_dir, name)
        dst = os.path.join(run_dir, name)
        if os.path.isfile(src) and os.path.splitext(name)[1].lower() in INPUT_SUFFIXES and not os.path.exists(dst):
            shutil.copy2(src, dst)
        elif os.path.isdir(src) and name in INPUT_DIR_ALLOWLIST and not os.path.exists(dst):
            shutil.copytree(src, dst)
    if os.path.basename(task_dir) == "csv_excel_48":
        normalize_csv_excel_48_headers(run_dir)

def get_args():
    parser = argparse.ArgumentParser(description="Run the SciDataInterpreter role")
    parser.add_argument("--task_id", type=str, help="Specify the task id. If not specified, all tasks will be run.")
    parser.add_argument("--data_source_type", type=str, help="Specify the data source. If not specified, all tasks will be run.")
    parser.add_argument("--max_runs", type=int, default=3, help="Maximum running times")
    parser.add_argument("--gt_prompt", type=str, help="Specify the ground truth prompt")
    parser.add_argument("--continue_gen", action="store_true", help="Continue the previous run")
    parser.add_argument("--output_dir", type=str, default="results", help="Specify the result root directory")
    parser.add_argument("--data_type", type=str, default="human", help="Specify the data type, including `csv`, `human`, `dl`, `bcb`")
    parser.add_argument("--skip_bcb", action="store_true", help="Skip the BCB data")
    # for scigentbench role
    parser.add_argument("--use_reflection", action="store_true", help="Use reflection")
    parser.add_argument("--hard_retry", action="store_true", help="Hard retry")
    parser.add_argument("--max_retry", type=int, default=None, help="Override TAME maximum retry times")
    parser.add_argument("--use_react", action="store_true", help="Use plan")
    parser.add_argument("--tame_variant", type=str, default="full_tame", help="TAME ablation variant")
    parser.add_argument("--tame_max_steps", type=int, default=None, help="Override T_plus execution budget")
    parser.add_argument(
        "--task-timeout-seconds",
        type=int,
        default=None,
        help="Optional wall-clock timeout for a single task run. Disabled by default.",
    )
    parser.add_argument("--list_tame_variants", action="store_true", help="List supported TAME variants and exit")
    # for customized config
    parser.add_argument("--config", default="test_config.yaml", type=str, help="Specify the config path")
    return parser.parse_args()

async def main(requirement: str, args=None):
    tame_config = TAMEConfig.from_variant(
        args.tame_variant,
        overrides={
            "max_steps": args.tame_max_steps,
            "max_retry": args.max_retry,
        },
    )
    if args.use_react:
        tame_config.planning = False
    if args.use_reflection:
        tame_config.adaptation = True
        tame_config.reflection = True
    react_mode = "plan_and_act" if tame_config.planning else "react"
    config = Config.from_yaml_file(resolve_config_path(args.config))
    # config = Config.from_sab_config(args.config)
    role = SciDataInterpreter(
        use_reflection=tame_config.reflection,
        hard_retry=args.hard_retry,
        max_retry=tame_config.max_retry,
        react_mode=react_mode,
        tame_config=tame_config,
        config=config
    )
    print(role.llm)
    print(role.llm.config)
    # print(role.actions[0].llm.config)
    role.actions[0].llm.config = config.llm
    role.planner.set_plan_writter(config)
    # print(role)
    # print(role.config.llm)
    try:
        if args.task_timeout_seconds:
            await asyncio.wait_for(role.run(requirement), timeout=args.task_timeout_seconds)
        else:
            await role.run(requirement)
    except asyncio.TimeoutError:
        logger.warning(
            f"Task timed out after {args.task_timeout_seconds} seconds; terminating this run and keeping partial artifacts."
        )
        await role.execute_code.terminate()

    return role.get_results_for_eval()

if __name__ == "__main__":
    # async def load_files():
    data_dir = "data/"
    folders = [f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))]
    num_folders = len(folders)
    args = get_args()
    if args.list_tame_variants:
        print("\n".join(item.value for item in TAMEVariant))
        raise SystemExit(0)
    if args.task_id is None:
        task_id = folders
    elif args.task_id in TASKSETS:
        task_id = TASKSETS[args.task_id]
    else:
        task_id = args.task_id if "[" not in args.task_id else eval(args.task_id)

    if isinstance(task_id, str):
        folders = [f"{args.task_id}"]
        num_folders = 1
    elif isinstance(task_id, list):
        folders = task_id
    else:
        pass

    # filter by data_source
    NaN = ''
    data_source_type = args.data_source_type
    filtered_folders = []
    for folder in folders:
        prompt_file = os.path.join(data_dir, folder, "prompt.json")
        if not os.path.exists(prompt_file):
            continue
        with open(prompt_file, "r") as file:
            prompt_data = eval(file.read())
            if data_source_type is None or prompt_data["data_source_type"].startswith(data_source_type):
                filtered_folders.append(folder)
    # folders=['bcb1011', 'bcb1017', 'bcb102', 'bcb1024', 'bcb1035', 'bcb1037', 'bcb104', 'bcb1043', 'bcb105', 'bcb1051']

    
    folders=filtered_folders
    # folders = list(reversed(filtered_folders))
    # print(folders)
    for id, folder in enumerate(folders):
        prompt_file = os.path.join(data_dir, folder, "prompt.json")
        # separately save each run
        for sub_idx in range(args.max_runs):
            with open(prompt_file, "r") as file:
                prompt_data = eval(file.read())
            # ===================================================
            # if orig_log_dir has already finished, skip
            # _, _, orig_log_dir, _ = create_logger(folder)
            # if os.path.getsize(os.path.join(orig_log_dir, "logs.txt")) != 0:
            #     print("Skipping folder", folder)
            #     continue
            # ===================================================
            tame_config = TAMEConfig.from_variant(
                args.tame_variant,
                overrides={
                    "max_steps": args.tame_max_steps,
                    "max_retry": args.max_retry,
                },
            )
            raw_model_name = get_model_name(args.config)
            model_dir_name = raw_model_name.split("/")[-1].replace("\\", "-").replace("/", "-")
            target_dir = f"{model_dir_name}__{tame_config.variant}_{sub_idx}"
            result_logger, time_logger, log_dir, run_dir = create_logger(
                folder,
                sub_idx,
                target_dir=target_dir,
                config_name=args.config,
                split=True,
                output_root=args.output_dir,
            )
            orig_log_file_path = os.path.join(log_dir)
            log_file_path = os.path.join(log_dir, "logs.txt")
            sys_log_file_path = os.path.join(log_dir, "sys_logs.txt")
            # sys_log_file_path = os.path.join(log_dir, "sys_logs.txt")

            # if os.path.getsize(sys_log_file_path) != 0:
            sys_log = ""
            if os.path.exists(sys_log_file_path):
                with open(sys_log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    sys_log = str(f.read())
            if "JSONDecodeError" in sys_log and "chatanywhere_error" not in sys_log:
                print("Skipping folder", folder)
                continue
            if os.path.getsize(log_file_path) != 0 and not args.continue_gen:
                print("Skipping folder", folder)
                continue

            # save misc. model statistics
            model_name = raw_model_name
            if not folder.startswith('bcb'):
                model_name = model_name.split("/")[-1]
            output_model_name = model_name.split("/")[-1].replace("\\", "-").replace("/", "-")
            output_dict_path = os.path.join(run_dir, f"{output_model_name}__{tame_config.variant}_outputs.jsonl")
            output_dict_path = os.path.abspath(output_dict_path)
            # specify where to load data and save data
            artifact_contract = build_artifact_contract(folder) if tame_config.t_plus else ""
            if not prompt_data["data_source_type"].startswith("1"):
                requirement = tame_contract_prompt(tame_config) + artifact_contract + SPECIFY_PATH_PROMPT + prompt_data["prompt"]
            else:
                requirement = tame_contract_prompt(tame_config) + artifact_contract + prompt_data["prompt"]
            if is_dsbench_task(folder):
                requirement = tame_contract_prompt(tame_config) + artifact_contract + dsbench_adapter_prompt()
                if not prompt_data["data_source_type"].startswith("1"):
                    requirement += SPECIFY_PATH_PROMPT
                requirement += prompt_data["prompt"]
            if folder == "csv_excel_48":
                requirement += CSV_EXCEL_48_NOTE
            # if 'bcb' in folder:
            #     requirement = BCB_OUTPUT_PROMPT + requirement
            if 'bcb' in folder and args.skip_bcb:
                print(f"Skipping {folder}")
                continue
            if args.data_type not in ("all", "*") and args.data_type not in folder:
                print(f"Skipping {folder}")
                continue
            if args.gt_prompt is not None:
                requirement = args.gt_prompt + '\n' + requirement
            # with change_dir(log_dir):
            sys_output_path = os.path.join(log_dir, "sys_logs.txt")
            task_dir_abs = os.path.abspath(os.path.dirname(prompt_file))
            # sys_output_path = os.path.abspath(sys_output_path)  # to avoid conflict with the change_dir context manager
            print(sys_output_path)
            print(output_dict_path)
            # redirect the log path for the metagpt logger
            with change_metalog_path(logger=logger, file_path=sys_output_path) as temp_logger:
                # redirect the pwd to the data folder
                with change_dir(log_dir):
                    try:
                        stage_task_inputs(task_dir_abs, os.getcwd())
                        if is_dsbench_task(folder):
                            created_adapter_files = ensure_adapter_files(os.getcwd())
                            if created_adapter_files:
                                temp_logger.info(f"DSBench adapter generated helper files: {created_adapter_files}")
                        temp_logger.info(f"Processing {folder} ({id}/{num_folders})")
                        temp_logger.info(f"Prompt:\n{requirement}")
                        
                        time_logger.info(f"Processing {folder} ({id}/{num_folders})")
                        start_time = time.time()
                        plan_list, cost_list, error_counter_list = asyncio.run(main(requirement, args))
                        if is_dsbench_task(folder):
                            adapter_result = normalize_final_answer(os.getcwd())
                            temp_logger.info(f"DSBench adapter postprocess: {adapter_result}")
                        end_time = time.time()
                        elapsed_time = end_time - start_time

                        temp_logger.info(f"Completed processing folder {folder} ({id+1}/{num_folders})")
                        temp_logger.info(f"Plan list:\n{plan_list}")
                        temp_logger.info(f"Cost list:\n{cost_list}")
                        temp_logger.info(f"Error counter list:\n{error_counter_list}")
                    
                        result_logger.info(f"Plan list:\n{plan_list}")
                        result_logger.info(f"Cost list:\n{cost_list}")
                        result_logger.info(f"Error counter list:\n{error_counter_list}")

                        time_logger.info(f"Elapsed time: {elapsed_time:.2f} seconds")

                        output_dict = SciAgentBenchOutput(
                            output_dir=log_dir,
                            time_cost=elapsed_time,
                            error_list=error_counter_list[-1],
                            cost=cost_list[-1],
                            plan=plan_list[-1],
                            tame_variant=tame_config.variant,
                            tame_layers=tame_config.as_layer_dict(),
                        )
                        output_dict = asdict(output_dict)

                        with open(output_dict_path, "a") as f:
                            f.write(json.dumps(output_dict)+'\n')

                    except Exception as e:
                        temp_logger.info("====================================================")
                        temp_logger.info(f"{e}\n====================================================")
                        result_logger.info(f"Run failed before producing a complete result: {e}")
                        elapsed_time = time.time() - start_time if "start_time" in locals() else 0
                        failure_plan = [
                            {
                                "task_id": "failed",
                                "dependent_task_ids": [],
                                "instruction": "Run failed before producing a complete structured plan",
                                "task_type": "data analysis",
                                "code": "",
                                "result": str(e),
                                "is_success": False,
                                "is_finished": True,
                            }
                        ]
                        output_dict = {
                            "output_dir": log_dir,
                            "time_cost": elapsed_time,
                            "error_list": [1],
                            "cost": {},
                            "plan": failure_plan,
                            "tame_variant": tame_config.variant,
                            "tame_layers": tame_config.as_layer_dict(),
                        }
                        with open(output_dict_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(output_dict, ensure_ascii=False) + "\n")
