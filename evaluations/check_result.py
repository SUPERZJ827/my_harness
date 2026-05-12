import os
import argparse
import shutil
import re

all_models = [ "Qwen/Qwen2.5-Coder-7B-Instruct", 
            "01-ai/Yi-1.5-9B-Chat-16K", "google/gemma-2-9b-it", "meta-llama/Meta-Llama-3-8B-Instruct", "meta-llama/Meta-Llama-3.1-8B-Instruct", "Qwen/Qwen2-1.5B-Instruct", "Qwen/Qwen2-7B-Instruct", "Qwen/Qwen2.5-7B-Instruct", "THUDM/glm-4-9b-chat"
            ]

def parse_arguments():
    parser = argparse.ArgumentParser(description="For Generation Progress Check")
    parser.add_argument("--model_id", type=str,help="Specify the model id")
    parser.add_argument("--runs_dir", type=str, default="results", help="Directory containing generated runs")

    args = parser.parse_args()
    return args

def main(all_args):
    all_should=[]
    dirs=[]
    output_dir = all_args.runs_dir
    model_ = all_args.model_id
    if model_ == "all":
        models = all_models
    else:
        models = [model_]

    for model_id in models:
        model_name = model_id.split('/')
        if len(model_name) > 1:
            model_dir=model_name[0]
            model_name = model_name[1]
        else:
            model_dir = ""
        have_completed = 0 
        success_num = 0
        bcb_num = 0
        dl_num = 0
        human_num = 0
        csv_num = 0
        # check progress on all tasks
        for dir_ in os.listdir(output_dir):
            flag = False
            new_dir = os.path.join(output_dir, dir_)
            if os.path.isdir(new_dir):
                should_dir_num=10
                actual_complete = 0
                success = 0
                for sub_dir in os.listdir(new_dir):
                    pattern = re.compile(rf"{model_name}_\d+")
                    if pattern.match(sub_dir):
                        sys_log_path = os.path.join(new_dir, sub_dir, 'sys_logs.txt')
                        if os.path.exists(sys_log_path) and os.path.getsize(sys_log_path) > 100:
                            actual_complete += 1
                        log_path = os.path.join(new_dir, sub_dir, 'logs.txt')
                        if os.path.exists(log_path) and os.path.getsize(log_path) > 10:
                            success += 1
                if actual_complete >7:
                    flag = True
                    have_completed += 1
                elif dir_ not in all_should:
                    all_should.append(dir_)
                if success > 0:
                    success_num += 1

                if flag:
                    pattern1="".join(filter(str.isalpha, dir_))
                    if pattern1 == "bcb":
                        bcb_num += 1
                    elif pattern1 == "dl":
                        dl_num += 1
                    elif pattern1 == "human":
                        human_num += 1
                    elif pattern1 == "csvexcel":
                        csv_num += 1

        # show results
        print(f"{model_id}")
        print(f"Number of tasks completed: {have_completed}")
        print(f"Number of successful tasks (i.e., JSON generated): {success_num}")
        print(f"Number of BCB tasks: {bcb_num}/167")
        print(f"Number of DL tasks: {dl_num}/10")
        print(f"Number of human tasks: {human_num}/25")
        print(f"Number of CSV tasks: {csv_num}/20\n")
    print(all_should)
if __name__ == '__main__':
    args = parse_arguments()
    main(args)
