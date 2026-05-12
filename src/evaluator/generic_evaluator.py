from src.schemas.schemas import Metric, Evaluator, Rule, TestFunction
from typing import Callable, Any

class GenericMetric(Metric):
    """
    A generic metric is instantiated with a function and the ground_truth of the given function. The function takes in the output and returns a metric
    """
    def __init__(self, f: TestFunction, ground_truth: Any):
        self.f = f
        self.gt = ground_truth

    def _get_metric(self):
        """Get the Generic Metric
        """
        return self.f.test(self.gt)
    

class GenericRule(Rule):
    """
    A generic rule is instantiated with a funciton that takes in a metric returned by the Metric class and returns a boolean
    """
    def __init__(self, rule: str=None):
        if rule == None:
            self.rule = lambda x: x
        else:
            self.rule = eval(rule)

    def _apply_rule(self, metric: Any) -> bool:
        """Apply the rule to the metric
        """
        return self.rule(metric)
    

class GenericEvaluator(Evaluator):
    def __init__(self, test_func: TestFunction, ground_truth: Any, rule: str=None):
        self.f = test_func
        self.gt = ground_truth
        self.metric_func = GenericMetric(test_func, ground_truth)
        self.rule_func = GenericRule(rule)

    def _evaluate(self) -> GenericMetric:
        """Evaluate the prompt on Generic Metric
        
        Args:
            - prompt (Any): The prompt to evaluate
        """
        metric = self.metric_func.get_metric()
        return self.rule_func.apply_rule(metric)
    
if __name__ == "__main__":
    pass