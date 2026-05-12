import os
import argparse
from utils.json_operator import *


def parse_arguments():
    parser = argparse.ArgumentParser(description="For Evaluation Verification")
    parser.add_argument("--task_id", type=str, default="bcb", help="Specify the task id, all bcb tasks by default")
    parser.add_argument("--model_id", type=str, default="gpt-4-turbo", help="Specify the model id")

    args = parser.parse_args()
    return args


def main(all_args):
    output_dir = 'data'
    model_id = all_args.model_id
    task_id = all_args.task_id
    for dir_ in os.listdir(output_dir):
        if os.path.isdir(os.path.join(output_dir, dir_)) and task_id in dir_:
            print(f"Verifying Prompt ID: --{dir_}--\n")
            prompt = read_json(os.path.join(output_dir, dir_, "prompt.json"))[0]["prompt"]
            output_file_path = os.path.join(output_dir, dir_, f"{model_id}_tmc_results.jsonl")
            output_datas = read_json(output_file_path)
            if not output_datas:
                # skip
                print("No output data found, skipping...")
                continue
            if len(output_datas) > 10:
                print(f"More than 10 results found, using first 10 results...")
                output_datas = output_datas[:10]
            for output_data in output_datas:
                completion_text = output_data['completion']
                cr = output_data['cr']
                print('-'*50, 'Prompt', '-'*50)
                print(prompt)
                print('-'*50, 'Completion', '-'*50)
                print(completion_text)
                print('-'*50, 'CR', '-'*50)
                print(cr)
                print('-'*50, 'Verification', '-'*50)
                ok = ''
                while ok not in ['y', 'n']:
                    ok = input("Is the evaluation result valid? (y/n)\n")
                if ok == 'y':
                    print("The result is valid. Moving to next data...")
                    continue
                else:
                    print("The result is invalid. Please check the output data...")
                    continue


if __name__ == '__main__':
    args = parse_arguments()
    main(args)
