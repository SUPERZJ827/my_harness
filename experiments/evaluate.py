import os
import argparse
import json
import ast
from src.utils import change_dir
from src.utils import load_yaml, list_to_dict_by_task
# from src.logs import create_logger, get_model_name
from src.schemas.dag import LinearizedDAG
from src.evaluator.cr_evaluator import CREvaluator
from dataclasses import dataclass
from typing import Union
import csv


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

def parse_arguments():
    parser = argparse.ArgumentParser(description="For evaluation")
    parser.add_argument("--requirement", type=str, default="", help="Specify the requirement")
    parser.add_argument("--plan", type=list, default=[], help="Specify the plan")
    parser.add_argument("--metric_path", type=str, help="Specify the path to the metric")
    parser.add_argument("--debug_mode", action="store_true", help="Specify the debug mode")
    parser.add_argument("--task_id", type=str, default="human_22", help="Specify the task id")
    parser.add_argument("--model_id", type=str, default="gpt-4-turbo-ca", help="Specify the model id")
    parser.add_argument("--runs_dir", type=str, default="results", help="Directory containing generated runs")
    parser.add_argument("--skip_vlm", action="store_true", help="Skip VLM/API-based evaluators and exclude them from CR")
    parser.add_argument("--include_bcb", action="store_true", help="Include BCB tasks in evaluation")

    args = parser.parse_args()
    return args


def normalize_task_ids(task_id_arg: str) -> set[str] | None:
    if task_id_arg == "all":
        return None
    text = str(task_id_arg).strip()
    if text == "original_full":
        data_dir = "data"
        if not os.path.isdir(data_dir):
            return None
        return {
            item
            for item in os.listdir(data_dir)
            if os.path.isdir(os.path.join(data_dir, item))
            and not item.startswith(("dabstep_", "dsbench_da_"))
        }
    if text in TASKSETS:
        return set(TASKSETS[text])
    if not text:
        return None
    if text.startswith("["):
        try:
            parsed = ast.literal_eval(text)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            return {str(item) for item in parsed}
    if "," in text:
        return {item.strip() for item in text.split(",") if item.strip()}
    return {text}

@dataclass
class FinalResultOutput:
    model_name: str
    run_id: int
    data_name: str
    task_name: str
    metric_name: str
    function_name: str
    result_value: str
    result_cr: Union[int, float]
    result_type: str = "single task (bool)"

    def to_list(self):
        return [self.model_name, self.run_id, self.data_name, self.task_name, self.metric_name, self.function_name, self.result_value, self.result_cr, self.result_type]


def get_result_output_dir(model_name):
    return os.path.join("evaluation_results", model_name+"_results.csv")


def is_vlm_metric(gt_dict: dict) -> bool:
    code = str(gt_dict.get("code", ""))
    metric = str(gt_dict.get("metric", ""))
    function = str(gt_dict.get("function", ""))
    task_name = str(gt_dict.get("task_name", ""))
    haystack = "\n".join([code, metric, function, task_name]).lower()
    return (
        "def vlm_judge" in haystack
        or "openai_api_key" in haystack
        or "openai_api_base" in haystack
        or "visual similarity" in haystack
        or "visual quality assessment" in haystack
    )


def main(requirement: str, plan: list, args):
    counter = 0
    total_counter = 0
    wrong_counter = 0
    silicon = [
        "Qwen/Qwen2.5-Coder-7B-Instruct",
        "01-ai/Yi-1.5-9B-Chat-16K", "google/gemma-2-9b-it", "meta-llama/Meta-Llama-3-8B-Instruct", "meta-llama/Meta-Llama-3.1-8B-Instruct", "Qwen/Qwen2-1.5B-Instruct", "Qwen/Qwen2-7B-Instruct", "Qwen/Qwen2.5-7B-Instruct", "THUDM/glm-4-9b-chat"
    ]
    model_name = args.model_id.split("/")[-1]
    selected_task_ids = normalize_task_ids(args.task_id)
    csv_output_file = get_result_output_dir(model_name)
    print("CSV output file: ", csv_output_file)
    csv_output_file = os.path.abspath(csv_output_file)
    with open(csv_output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["model_name", "run_id", "data_name", "task_name", "metric_name", "function_name", "result_value", "result_cr", "result_type"])  # Write the header
    # Evaluate each runs_dir/task_id/model_name_sub_idx/ with metric/task_id
    for data_task_id in os.listdir('data'):
        if os.path.isdir(os.path.join('data', data_task_id)):
            total_counter += 1
        metric_task_id = data_task_id  # Assuming the metric/task_id has the same name as data/task_id
        # if args.model_id in silicon:
            # data_path = os.path.join('data', data_task_id, args.model_id.split("/")[0])
            # print("Data path: ", data_path)
        # else:
        data_path = os.path.join('data', data_task_id)
        runs_path = os.path.join(args.runs_dir, data_task_id)
        if selected_task_ids is not None and data_task_id not in selected_task_ids:
            continue
        if 'bcb' in data_task_id and not args.include_bcb:
            continue

        metric_dir = os.path.join('metric', metric_task_id)
        if not os.path.isdir(metric_dir):
            print(f"Metric for {metric_task_id} is not found!")
            continue
        metric_path = os.path.join(metric_dir, "metric.yaml")

        # Load the metric and perform evaluation
        metric_config = load_yaml(metric_path)
        # print(metric_config['TMC-list'])
        # print("Length: ", len(metric_config['TMC-list']))
        task_to_gt = list_to_dict_by_task(metric_config['TMC-list'])

        # output_name = f"{model_name}_outputs.jsonl"
        outputs = []
        # for loading the outputs
        true = True
        false = False
        if not os.path.isdir(runs_path):
            print(f"Runs for {data_task_id} are not found under {args.runs_dir}! Skipped.")
            continue

        # print("Runs path: ", os.listdir(runs_path))
        for model_run_id in os.listdir(runs_path):
            if args.model_id is not None and not model_run_id.startswith(args.model_id.split("/")[-1]):
            # if args.model_id is not None and not model_run_id in args.model_id:
                continue
            # if args.model_id in silicon:
                
            # else:
            #     model_name = '_'.join(model_run_id.split("_")[:-1])
            run_id = model_run_id.split("_")[-1]
            # if not os.path.exists(csv_output_file):
 
            print("Evaluating ", model_run_id)
            if '-ui' in model_run_id:
                output_dict = {}
                output_dict['dir'] = os.path.join(runs_path, model_run_id)
                output_dict['model_name'] = model_name
                output_dict['run_id'] = run_id
                outputs.append(output_dict)
            elif os.path.exists(os.path.join(runs_path, model_run_id, "logs.txt")) and os.path.getsize(os.path.join(runs_path, model_run_id, "logs.txt")) != 0:
                output_dict = {}
                output_dict['dir'] = os.path.join(runs_path, model_run_id)
                output_dict['model_name'] = model_name
                output_dict['run_id'] = run_id
                outputs.append(output_dict)
                counter += 1
            elif args.debug_mode or model_run_id == 'gt':
                output_dict = {}
                output_dict['dir'] = os.path.join(runs_path, model_run_id)
                output_dict['model_name'] = model_name
                output_dict['run_id'] = run_id
                outputs.append(output_dict)
                counter += 1
            else:
                print(f"Model run {model_run_id} is invalid! Skipped.")
        
        # save the results per model run and per task to a single file
        for idx, output in enumerate(outputs):
            gt_path = os.path.abspath(data_path)
            # if args.model_id in silicon:
            #     gt_path = os.path.join(gt_path, "../gt")
            # else:
            gt_path = os.path.join(gt_path, "gt/")
            model_name = output['model_name']
            run_id = output['run_id']
            for key in task_to_gt:
                if "ground_truth" not in task_to_gt[key]:
                    print(f"Ground truth for {key} is not configured yet! Using {gt_path} as default")
                    task_to_gt[key]["ground_truth"] = gt_path
                else:
                    task_to_gt[key]['ground_truth'] = os.path.normpath(os.path.join(gt_path, task_to_gt[key]['ground_truth']))
                    print(f"Ground truth is {task_to_gt[key]['ground_truth']}")

            with change_dir(output['dir']):
                # print the paths
                print(f"Evaluating {data_path}")
                print("="*100)
                print(f"= Path to ground truth: {gt_path}")
                print("="*100)

                # initialize the dag using TFCs
                linearized_dag = LinearizedDAG(requirement, task_to_gt, force_mode=True)
                dag = linearized_dag.get_dag("")
                cr_list = []
                result_output_list = [] # store the tuple of (result, task_name)
                # wrong_flag = False
                for node in dag:
                    temp_cr_score = 0
                    temp_result_value = ""
                    result_type = "single task (bool)"
                    if args.skip_vlm and is_vlm_metric(task_to_gt.get(node.task_type, {})):
                        print(f"Skipping VLM metric: {node.task_name} / {node.metric} / {node.function}")
                        output_item = FinalResultOutput(
                            model_name=model_name,
                            run_id=run_id,
                            data_name=data_task_id,
                            task_name=node.task_name,
                            metric_name=node.metric,
                            function_name=node.function,
                            result_value="Skipped",
                            result_cr=0,
                            result_type="skipped"
                        )
                        result_output_list.append(output_item)
                        continue
                    # print(f"Node {node} is being evaluated")
                    if len(node.evaluator_list) != 0:
                        print("Function: ", node.evaluator_list[0].f.f)
                    try:
                        result = node.evaluate_node()
                        if len(result) > 1:
                            print("!!!!!!!!!")
                            print(result)
                        if result is not None:
                            for result_item in result:
                                print(result_item)
                                # for VLM
                                if isinstance(result_item, float):
                                    print("Result item is integer")
                                    print(result_item)
                                    if result_item >= 3:
                                        print("Evaluation result: Successful! Score: 2")
                                        temp_cr_score = 2
                                        cr_list.append(2)
                                        temp_result_value = str(int(result_item))
                                        result_type = "single task (int)"
                                    else:
                                        print("Evaluation result: Failed! Score: 1")
                                        temp_cr_score = 1
                                        cr_list.append(1)
                                        temp_result_value = str(int(result_item))
                                        result_type = "single task (int)"
                                else:
                                    result_item = bool(result_item)
                                # if isinstance(result_item, bool):
                                    print(result_item)
                                    if result_item:
                                        print("Evaluation result: Successful! Score: 2")
                                        temp_cr_score = 2
                                        cr_list.append(2)
                                        temp_result_value = "True"
                                    else:
                                        print("Evaluation result: Passed but not successful! Score: 1")
                                        temp_cr_score = 1
                                        cr_list.append(1)
                                        temp_result_value = "False"
                        print("="*100)
                    except Exception as e:
                        print("Evaluation result: Failed! Score: 0")
                        print("Error:")
                        print(e)
                        print("="*100)
                        print()
                        temp_cr_score = 0
                        cr_list.append(0)
                        temp_result_value = "Error"
                        result_type = "single task"
                        # print(e)
                    output_item = FinalResultOutput(
                        model_name=model_name,
                        run_id=run_id,
                        data_name=data_task_id,
                        task_name=node.task_name,
                        metric_name=node.metric,
                        function_name=node.function,
                        result_value=temp_result_value,
                        result_cr=temp_cr_score,
                        result_type=result_type
                    )
                    result_output_list.append(output_item)

                scored_result_count = sum(1 for item in result_output_list if item.result_type != "skipped")
                assert len(cr_list) == scored_result_count, f"Length of cr_list ({len(cr_list)}) and scored result_output_list ({scored_result_count}) do not match!"
                if cr_list:
                    CR = CREvaluator.calcualte_cr(cr_list)
                    CR_item = FinalResultOutput(
                        model_name=model_name,
                        run_id=run_id,
                        data_name=data_task_id,
                        task_name="Completion Rate",
                        metric_name="CR",
                        function_name="CR",
                        result_value=str(CR),
                        result_cr=CR,
                        result_type="Completion Rate"
                    )
                else:
                    CR_item = FinalResultOutput(
                        model_name=model_name,
                        run_id=run_id,
                        data_name=data_task_id,
                        task_name="Completion Rate",
                        metric_name="CR",
                        function_name="CR",
                        result_value="Skipped",
                        result_cr=0,
                        result_type="skipped"
                    )
                result_output_list.append(CR_item)

            results = []
            for result_output in result_output_list:
                results.append(result_output.to_list())

            # Write the results to the CSV file
            with open(csv_output_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                # writer.writerow(["model_name", "data_name", "task_name", "result"])  # Write the header
                writer.writerows(results)  # Write the results

        # pass@k calculation
        # if pass_k > 0:
        #     passes += 1
        # else:
        #     print(f"Failed to evaluate {data_task_id}")
        #     return
            # Print the number of successful evaluations and unsuccessful evaluations

    print("Total number of total counter:", total_counter)
    print("Total number of wrongs:", wrong_counter)
    # print("Total number of passes:", passes)
    
    # return CR


if __name__ == "__main__":
    args = parse_arguments()
    requirement = args.requirement
    plan = args.plan
    main(requirement, plan, args)
