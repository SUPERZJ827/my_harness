from abc import ABC
from typing import Any
from dataclasses import dataclass
# from metagpt.strategy.task_type import TaskType
from src.utils import create_function_from_string

class Evaluator(ABC):
    def __init__(self):
        pass

    def evaluate(self, **kwargs):
        """The method to evaluate a prompt
        """

        return self._evaluate(**kwargs)

    def _evaluate(self, **kwargs):
        """The method to evaluate a prompt. Should be inhereted
        """

        raise NotImplementedError("Method evaluate not implemented")

@dataclass    
class Task:
    task_type: str
    desc: str = None
    
class Metric(ABC):
    def __init__(self):
        pass

    def get_metric(self, **kwargs):
        """The method to get the metric
        """

        return self._get_metric(**kwargs)

    def _get_metric(self, **kwargs):
        """The method to get the metric. Should be inhereted
        """

        raise NotImplementedError("Method get_metric not implemented")

class Rule(ABC):
    def __init__(self):
        pass

    def apply_rule(self, metric: Any, **kwargs):
        """The method to apply the rule
        """

        return self._apply_rule(metric, **kwargs)

    def _apply_rule(self, metric, **kwargs):
        """The method to apply the rule. Should be inhereted
        """

        raise NotImplementedError("Method apply_rule not implemented")
    
class TestFunction:
    """The Code in (T, M, C) schema. Used to accept the ground truth output 
        and the test output and then return the Metric.
    """
    def __init__(self, f: str):
        self.func_name, self.f = create_function_from_string(f)

    def test(self, gt_output: Any):
        """
        The method to test the metric. When passing this to the Evaluator, we do `f = partial(test_funciton, gt_output)`, 
        so the `metric = f(test_output)` will be called to get the metric.

        Optionally, we can also just retrieve the ground truth output and the test output and then call the `test` method.
        """

        return self._test(gt_output)

    def _test(self, gt_output: Any):
        """The method to test the code. Should be inhereted
        """

        return self.f(gt_output)
    
class DAG(ABC):
    def __init__(self):
        pass

@dataclass
class SciAgentBenchOutput:
    output_dir: str
    time_cost: float
    error_list: list
    cost: list
    plan: list
    tame_variant: str = ""
    tame_layers: dict = None
