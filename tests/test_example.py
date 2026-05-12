import unittest
from src.schemas.dag import Node, LineairzedDAG
from src.utils import load_yaml, list_to_dict_by_task

async def run_di(prompt: str):
    test_dag = LineairzedDAG(prompt)
    test_dag.launch_test()

class TestExample(unittest.TestCase):
    passed_tests_counter = 0

    @classmethod
    def setUpClass(cls):
        cls.config = load_yaml("tests/testcases/example.yaml")
        cls.task_to_gt = list_to_dict_by_task(cls.config['TMC-list'])

        

    def test_larger_than(self):
        pass

    def test_distance(self):
        distance = 0

        self.assertLess(distance, 10)

def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMathUtils)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    return TestExample.passed_tests_counter

if __name__ == "__main__":
    passed_tests = run_tests()
    print(f"\nTotal passed tests: {passed_tests}")
