from src.schemas.schemas import Metric, Evaluator, TestFunction, Rule
from typing import Callable, Any

class LargerthanMetric(Metric):
    def __init__(self, f: TestFunction, ground_truth: Any):
        self.f = f
        self.gt = ground_truth

    def _get_metric(self, output):
        """Get the Generic Metric
        """
        
        return self.f.test(self.gt, output)
    

class LargerthanRule(Rule):
    def __init__(self, rule: str):
        self.rule = eval(rule)

    def _apply_rule(self, metric: Any, **kwargs):
        return self.rule(metric)
    

class LargerthanEvaluator(Evaluator):
    def __init__(self, test_func: TestFunction, ground_truth: Any, rule: str, **kwargs):
        self.f = test_func
        self.gt = ground_truth
        self.rule = LargerthanRule(rule)

    def _evaluate(self, output: Any, **kwargs) -> Metric:
        """Evaluate the prompt on Generic Metric
        
        Args:
            - prompt (Any): The prompt to evaluate
        """
        metric = LargerthanMetric(self.f, self.gt).get_metric(output)
        return self.rule.apply_rule(metric)