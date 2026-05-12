import os
import argparse
from utils.json_operator import *
import shutil


def parse_arguments():
    parser = argparse.ArgumentParser(description="For Evaluation Result Display")
    parser.add_argument("--task_id", type=str, default="bcb", choices=["bcb"],
                        help="Specify the task id, all bcb tasks by default")
    parser.add_argument("--model_id", type=str, default="gpt-4-turbo", help="Specify the model id")

    args = parser.parse_args()
    return args


def main(all_args):
    output_dir = 'data'
    model_id = all_args.model_id
    task_id = all_args.task_id
    all_crs = []
    all_success_rates = []

    # check results on all tasks
    for dir_ in os.listdir(output_dir):
        if os.path.isdir(os.path.join(output_dir, dir_)) and task_id in dir_:
            # print(f"Evaluating Prompt ID: --{dir_}--\n")
            output_file_path = os.path.join(output_dir, dir_, f"{model_id}_tmc_results.jsonl")
            output_datas = read_json(output_file_path)
            completed_n = len(output_datas)
            crs = []
            for i in range(10):
                if i >= completed_n:
                    crs.append(0)
                else:
                    crs.append(output_datas[i]["cr"])
            success = [cr >= 1.0 for cr in crs]
            avg_cr = sum(crs) / len(crs)
            success_rate = sum(success) / len(success)
            all_crs.append(avg_cr)
            all_success_rates.append(success_rate)

    # calculate pass@1 results
    pass_1_rate = sum(all_success_rates) / len(all_success_rates)
    total_avg_cr = sum(all_crs) / len(all_crs)
    print(f"--Results for {model_id} on {task_id}--\nPass@1 Rate: {pass_1_rate}\nAverage CR: {total_avg_cr}\n")
    output_file_name = f"results/{task_id}/{model_id}_results.json"
    output_js = [{"pass_1_rate": pass_1_rate, "avg_cr": total_avg_cr}]
    dump_json(output_file_name, output_js)


if __name__ == "__main__":
    args = parse_arguments()
    main(args)
