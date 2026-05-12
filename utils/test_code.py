test_comp_func = '''
import concurrent
future = executor.submit(task_func, *args)
print('Function submitted to executor...\\n')
try:
    cur_completion_output = future.result(timeout=120)
except concurrent.futures.TimeoutError:
    executor.shutdown(wait=False)
    raise TimeoutError('Function did not complete within 120s!\\n')
if not isinstance(cur_completion_output, tuple):
    cur_completion_output = (cur_completion_output,)
'''
test_gt_func = '''
gt_output = task_func(*args)
'''
test_metric_func = '''
import numpy as np
metric_output = {metric_func_name}(cur_completion_output, gt_output)
if isinstance(metric_output, np.bool_):
    metric_output = bool(metric_output)
metric_output = float(metric_output)
print('<metric_output>\\n', metric_output)
'''
