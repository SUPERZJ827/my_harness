from .schemas import Metric, Evaluator, Task, TestFunction, DAG
from ..evaluator.evaluator_dict import TM_2_EVALUATOR
from ..evaluator import GenericEvaluator, CREvaluator
from role import SciDataInterpreter
import warnings

class Node:
    def __init__(self, node_info: dict, taskname2gt: dict[dict]=None, task_list: list[Task]=None):
        """
        There are two kinds of Nodes:
        - a Node that does not need to be evaluated
        - a Node needs to be evaluated. In this case, the Node will retrieve Evaluators which include Metrics, Codes and Rules.
        """
        self.correct_list = []
        self.task_id = node_info.get("task_id", None)
        self.function = node_info.get("function", None)
        self.metric = node_info.get("metric", None)
        self.dependent_task_ids = node_info.get("dependent_task_ids", None)
        self.instruction = node_info.get("instruction", None)
        self.task_type = node_info.get("task_type", None)
        self.task_name = node_info.get("task_name", None)
        self.code = node_info.get("code", None)
        self.result = node_info.get("result", None)
        self.is_success = node_info.get("is_success", None)
        self.is_finished = node_info.get("is_finished", None)
        self.taskname2gt = taskname2gt
        if task_list is None:
            self.task_list = self.retrieve_task(self.task_type)
        else:
            self.task_list = task_list
        self.evaluator_list = []
        for task in self.task_list:
            self.evaluator_list.append(self.retrieve_evaluator(task, taskname2gt))

    @classmethod
    def from_taskname2gt(cls, task_name, gt_dict, task_list=None):
        """
        Class method to instantiate the class with taskname2gt
        """
        node_info = {
            "task_type": task_name,
            "task_name": gt_dict['task_name'],
            "function": gt_dict['function'],
            "metric": gt_dict['metric']
        }
        taskname2gt = {
            task_name: gt_dict
        }
        return cls(node_info, taskname2gt, task_list)
    
    def retrieve_task(self, task_type: str):
        """
        The method to retrieve the task
        """
        task_list = []
        # print(self.taskname2gt)
        for taskname in self.taskname2gt:
            if task_type.lower() in taskname.lower():
                task_list.append(Task(taskname, self.instruction))

        return task_list
    
    def retrieve_evaluator(self, task: Task, taskname2gt: dict[dict]=None):
        """
        The method to retrieve the evaluator
        """
        evaluator = TM_2_EVALUATOR.get(task.task_type, GenericEvaluator)
        if task.task_type == "CR":
            return evaluator()
        if evaluator is None:
            return None
        gt_dict = taskname2gt.get(task.task_type, None)
        # print(gt_dict)
        if gt_dict is None:
            return None
        else:
            code = TestFunction(gt_dict.get("code", None))
            # TODO: add the logic to determine which metric to use
            # metric = gt_dict.get("metric", None)

            return evaluator(
                test_func = code,
                ground_truth = gt_dict.get("ground_truth", None),
                rule=gt_dict.get("rule", None)
                )

    def evaluate_node(self, **kwargs):
        """
        The method to evaluate the Node
        """
        # print pwd
        import os
        print("Current dir is: ", os.path.abspath(os.curdir))
        # TODO: there can also be metric over surface form, but only consider the metric over the output for now
        result_list = []
        for evaluator in self.evaluator_list:
            # print(f"Evaluator {evaluator} is evaluating result of type {type(self.result)}:\n{self.result}")
            correctness = evaluator.evaluate()
            # make sure the evaluator only returns 0 or 1
            if isinstance(correctness, int):
                assert correctness in [0, 1]
                self.correct_list.append(correctness)
            elif isinstance(correctness, bool):
                self.correct_list.append(int(correctness))
            else:
                self.correct_list.append(1)
                print(correctness)
                wrong_type = type(correctness)
                warnings.warn(f"The evaluator should return either an integer or a boolean, but a {wrong_type} was returned.")
            result_list.append(correctness)
        if len(result_list) > 0:
            return result_list
        else:
            return None
        # self.evaluator.evaluate(
        #     output=self.result,
        #     is_success=self.is_success,
        #     is_finished=self.is_finished,
        # )

class LinearizedDAG(DAG):
    """
    The Linearized DAG class

    Args:
        - prompt (str): The prompt to evaluate
        - taskname2gt (dict[dict]): a dictionary where keys are task name and values are dictionary containing the ground-truths
    """
    def __init__(self, prompt: str, taskname2gt: dict[dict]=None, force_mode=False):
        self.force_mode = force_mode
        self.prompt = prompt
        self.taskname2gt = taskname2gt
        # self.role = SciDataInterpreter()

    # async def get_results(self):
    #     await self.role.run(self.prompt)
    #     return self.role.get_results_for_eval()

    async def launch_test(self):
        """
        The method to launch the test

        Nodes in the Linearized DAG will be tested first. After the tests of all Nodes are finished, the Completion Rate Node will be tested.
        """
        plan_list, cost_list, error_counter_list = await self.get_results(self.prompt)
        self.dag = self.get_dag(plan_list[-1])    # the linearized DAG is a list of Nodes, and we test each Node in the list. Use the last plan in the list.
        # block until get_results is finished
        # test each Node
        # test the Completion Rate Node
        for node in self.dag:
            node.evaluate_node()

        self.CR_evaluator = CREvaluator()
        self.CR = self.CR_evaluator.evaluate(self.dag)

        return self.CR
        
    def get_dag(self, plan: list[dict]):
        """The method to get the DAG
        """
        dag = []
        if not self.force_mode:
            for node in plan:
                dag.append(Node(node, self.taskname2gt))

            return dag
        else:
            print("Using force mode")
            for task_name, gt_dict in self.taskname2gt.items():
                # print(task_name)
                # print(gt_dict)
                dag.append(Node.from_taskname2gt(task_name, gt_dict, task_list=[Task(task_name, desc="")]))
            # print(dag)
            return dag
        
if __name__ == "__main__":
    # test the code
    prompt = "Test the code"
    test_dag = LinearizedDAG(prompt)
    test_dag.launch_test()