import os
import argparse
from src.utils import load_yaml, list_to_dict_by_task
from utils.test_code import *
from utils.json_operator import *
from utils.used_libs import *
from utils.cr_for_bcb import *
import shutil
import concurrent.futures


def parse_arguments():
    parser = argparse.ArgumentParser(description="For TMC Evaluation")
    parser.add_argument("--metric_dir", type=str, default="metric", help="Specify the path to the metric")
    parser.add_argument("--task_id", type=str, default="bcb", help="Specify the task id, all bcb tasks by default")
    parser.add_argument("--model_id", type=str, default="gpt-4-turbo-ca", help="Specify the model id")

    args = parser.parse_args()
    return args


def extract_answer_func(plan: list) -> str:
    ans = ""
    func_defined = False
    for item in plan:
        task_code = item['code']
        if 'def task_func' in task_code:
            if func_defined and 'return' in ans.split('def task_func')[1]:
                break
            else:
                func_defined = True
        ans = ans + task_code
        lines = task_code.strip().split("\n")
        if 'return' in lines[-1] and func_defined:
            break
    return ans


def main(all_args):
    output_dir = 'data'
    metric_dir = all_args.metric_dir
    model_id = all_args.model_id
    task_id = all_args.task_id
    abs_dir = os.getcwd()

    # eval all tasks
    if task_id == "all":
        for dir_ in os.listdir(output_dir):
            if os.path.isdir(os.path.join(output_dir, dir_)):
                print(f"Evaluating Prompt ID: --{dir_}--\n")
                metric_file_path = os.path.join(metric_dir, dir_, "metric.yaml")
                metric_config = load_yaml(metric_file_path)
                gt_func = metric_config['ground_truth']
                inputs = metric_config['data']
                TMCs = metric_config['TMC-list']
                output_file_path = os.path.join(output_dir, dir_, f"{model_id}_outputs.jsonl")
                output_datas = read_json(output_file_path)
                if not output_datas:
                    # skip
                    continue
                new_datas = []
                for cur_data in output_datas:
                    os.chdir(abs_dir)
                    new_data = {"output_dir": cur_data['output_dir'], "time_cost": cur_data['time_cost'],
                                "error_list": cur_data['error_list'], "cost": cur_data['cost']}
                    cur_answer = extract_answer_func(cur_data['plan'])
                    new_data.update({"completion": cur_answer})
                    print(f'<Extracted answer function>\n{cur_answer}')
                    cur_completion_output = None
                    gt_output = None
                    try:
                        temp_dict = {}
                        exec(inputs, locals())
                        print('Inputs loaded...')
                        if 'pip' in cur_answer or 'os.system' in cur_answer:
                            raise Exception('Pip or os.system is not allowed!')
                        if cur_answer.count('def task_func') > 2:
                            # only one extra announcement is allowed
                            raise Exception('Multiple task_func definitions are not allowed!')
                        exec(cur_answer, locals())
                        print('Answer function defined...')
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            print('Testing answer function with ThreadPoolExecutor...')
                            exec(test_comp_func, locals(), temp_dict)
                        print('Answer function tested...')
                        exec(gt_func, locals())
                        print('Ground truth function defined...')
                        exec(test_gt_func, locals(), temp_dict)
                        print('Ground truth function tested...')
                        print('Evaluating CR...')
                        cur_completion_output = temp_dict['cur_completion_output']
                        gt_output = temp_dict['gt_output']
                        try:
                            cr_value = evaluate_cr(temp_dict['cur_completion_output'], temp_dict['gt_output'])
                            new_data.update({'cr': cr_value})
                        except Exception as e_:
                            print('Error occurred when evaluating CR!')
                            print('<Error type>\n', e_)
                            new_data.update({'cr': 0})
                    except Exception as e:
                        print('Error occurred!')
                        print('<Error type>\n', e)
                        new_data.update({'cr': 0})
                        TMC_results = []
                        for TMC in TMCs:
                            TMC_item = {"function": TMC['function'], 'result': None}
                            TMC_results.append(TMC_item)
                            print('-' * 50)
                        new_data.update({"TMC_results": TMC_results})
                        new_datas.append(new_data)
                        continue

                    TMC_results = []
                    for TMC in TMCs:
                        TMC_item = {"function": TMC['function'], 'task_name': TMC['task_name']}
                        func_code = TMC['code']
                        metric_func_name = func_code.split('def')[1].split('(')[0].strip()
                        try:
                            temp_dict = {}
                            exec(func_code, locals())
                            print('Metric function defined...')
                            exec(test_metric_func.format(metric_func_name=metric_func_name), locals(), temp_dict)
                            print('Metric calculated...')
                            TMC_item.update({'result': temp_dict['metric_output']})
                        except Exception as e:
                            print('Error occurred!')
                            print('<Error type>\n', e)
                            TMC_item.update({'result': None})

                        print('-' * 50)
                        TMC_results.append(TMC_item)
                    new_data.update({"TMC_results": TMC_results})
                    new_datas.append(new_data)
                result_file_path = os.path.join(output_dir, dir_, f"{model_id}_tmc_results.jsonl")
                dump_json(result_file_path, new_datas)
                print("Results exported...\n")

    # eval specified tasks
    else:
        for dir_ in os.listdir(output_dir):
            if os.path.isdir(os.path.join(output_dir, dir_)) and task_id in dir_:
                print(f"Evaluating Prompt ID: --{dir_}--\n")
                metric_file_path = os.path.join(metric_dir, dir_, "metric.yaml")
                metric_config = load_yaml(metric_file_path)
                gt_func = metric_config['ground_truth']
                inputs = metric_config['data']
                TMCs = metric_config['TMC-list']
                output_file_path = os.path.join(output_dir, dir_, f"{model_id}_outputs.jsonl")
                output_datas = read_json(output_file_path)
                if not output_datas:
                    # skip
                    continue
                new_datas = []
                for cur_data in output_datas:
                    os.chdir(abs_dir)
                    new_data = {"output_dir": cur_data['output_dir'], "time_cost": cur_data['time_cost'],
                                "error_list": cur_data['error_list'], "cost": cur_data['cost']}
                    cur_answer = extract_answer_func(cur_data['plan'])
                    new_data.update({"completion": cur_answer})
                    print(f'<Extracted answer function>\n{cur_answer}')
                    cur_completion_output = None
                    gt_output = None
                    try:
                        temp_dict = {}
                        exec(inputs, locals())
                        print('Inputs loaded...')
                        if 'pip' in cur_answer or 'os.system' in cur_answer:
                            raise Exception('Pip or os.system is not allowed!')
                        if cur_answer.count('def task_func') > 2:
                            # only one extra announcement is allowed
                            raise Exception('Multiple task_func definitions are not allowed!')
                        exec(cur_answer, locals())
                        print('Answer function defined...')
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            print('Testing answer function with ThreadPoolExecutor...')
                            exec(test_comp_func, locals(), temp_dict)
                        print('Answer function tested...')
                        exec(gt_func, locals())
                        print('Ground truth function defined...')
                        exec(test_gt_func, locals(), temp_dict)
                        print('Ground truth function tested...')
                        print('Evaluating CR...')
                        cur_completion_output = temp_dict['cur_completion_output']
                        gt_output = temp_dict['gt_output']
                        try:
                            cr_value = evaluate_cr(temp_dict['cur_completion_output'], temp_dict['gt_output'])
                            new_data.update({'cr': cr_value})
                        except Exception as e_:
                            print('Error occurred when evaluating CR!')
                            print('<Error type>\n', e_)
                            new_data.update({'cr': 0})
                    except Exception as e:
                        print('Error occurred!')
                        print('<Error type>\n', e)
                        new_data.update({'cr': 0})
                        TMC_results = []
                        for TMC in TMCs:
                            TMC_item = {"function": TMC['function'], 'result': None}
                            TMC_results.append(TMC_item)
                            print('-' * 50)
                        new_data.update({"TMC_results": TMC_results})
                        new_datas.append(new_data)
                        continue

                    TMC_results = []
                    for TMC in TMCs:
                        TMC_item = {"function": TMC['function'], 'task_name': TMC['task_name']}
                        func_code = TMC['code']
                        metric_func_name = func_code.split('def')[1].split('(')[0].strip()
                        try:
                            temp_dict = {}
                            exec(func_code, locals())
                            print('Metric function defined...')
                            exec(test_metric_func.format(metric_func_name=metric_func_name), locals(), temp_dict)
                            print('Metric calculated...')
                            TMC_item.update({'result': temp_dict['metric_output']})
                        except Exception as e:
                            print('Error occurred!')
                            print('<Error type>\n', e)
                            TMC_item.update({'result': None})

                        print('-' * 50)
                        TMC_results.append(TMC_item)
                    new_data.update({"TMC_results": TMC_results})
                    new_datas.append(new_data)
                result_file_path = os.path.join(output_dir, dir_, f"{model_id}_tmc_results.jsonl")
                dump_json(result_file_path, new_datas)
                print("Results exported...\n")


# run
if __name__ == "__main__":
    # exec(import_libs)
    arguments = parse_arguments()
    main(arguments)
    if os.path.exists('data/task_func'):
        shutil.rmtree('data/task_func')
