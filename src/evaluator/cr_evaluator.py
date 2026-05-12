from src.schemas.schemas import Metric, Evaluator, DAG
import json
import asyncio

# from metagpt.roles.di.data_interpreter import DataInterpreter
# from role import SciDataInterpreter
from metagpt.logs import logger

from metagpt.schema import Message, Task, TaskResult, Plan

class CRMetric(Metric):
    # CR: int = None
    plan_list: list[Plan] = []

    def __init__(self, plan_list):

        self.plan_list = plan_list

    def _get_metric(self):
        """Get the Completion Rate Metric
        """
        
        return self._calculate_CR()
    
    def _calculate_CR(self):
        """Calculate the Completion Rate
        """
        json_objects = self.read_json_from_list(self.plan_list)
        return self.calculate_completion_rate_from_json(json_objects)

    # helper func 1
    def read_json_from_list(self, plan):
        content = str(plan)
        # Remove any non-JSON content
        json_start_pos = content.find("## Current Plan")
        json_end_pos = content.find("## Current Task")
        content = content[json_start_pos+16:json_end_pos]
        json_objects = json.loads(content)
        return json_objects

    # helper func 2
    def compliant_with_Ground_Truth(self, task):
        return False

    # helper func 3
    def calculate_completion_rate_from_json(self, json_objects):
        total_tasks = len(json_objects)
        l = []
        for task in json_objects:
            if task['is_success'] and task['is_finished']:
                if self.compliant_with_Ground_Truth(task):
                    l.append(2)
                else:
                    l.append(1)
            else:
                l.append(0)
        successful_tasks = sum(l)
        completion_rate = successful_tasks / (total_tasks*2)
        return completion_rate
    
class CREvaluator(Evaluator):
    def __init__(self):
        pass

    @classmethod
    def calcualte_cr(self, cr_list):
        max_scores = len(cr_list) * 2
        scores = sum(cr_list)
        metric = scores / max_scores

        return metric

    def _evaluate(self, dag: list) -> Metric:
        """Evaluate the prompt on Completion Rate
        
        Args:
            - prompt (str): The prompt to evaluate
        """
        max_scores = 0
        scores = 0
        for node in dag:
            max_scores += len(node.correct_list) * 3
            scores += sum(node.correct_list) * 2 + len(node.correct_list) * int(node.is_success)
        
        # TODO: maybe no need to use Metric here
        metric = scores / max_scores
        return metric