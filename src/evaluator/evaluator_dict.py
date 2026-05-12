from ..schemas.schemas import Metric, Evaluator
from .cr_evaluator import CREvaluator
from .within_range_evaluator import WithinRangeEvaluator
from .larger_than_evaluator import LargerthanEvaluator

TM_2_EVALUATOR = {
    "CR": CREvaluator,
    "test_bool": WithinRangeEvaluator,
    "test_int": LargerthanEvaluator
}