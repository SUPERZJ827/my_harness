from src.utils import load_yaml, list_to_dict_by_task, create_function_from_string
import unittest

class TestUtils(unittest.TestCase):
    
    def test_load_yaml(self):
        self.config = load_yaml("tests/testcases/example.yaml")
        print(list_to_dict_by_task(self.config['TMC-list']))

    def test_create_function_from_string(self):
        self.config = load_yaml("tests/testcases/example.yaml")
        func_name, self.func = create_function_from_string(self.config['TMC-list'][0]['code'])
        self.rule = eval(self.config['TMC-list'][0]['rule'])

    def test_yaml_function(self):
        self.config = load_yaml("tests/testcases/example.yaml")
        func_name, self.func = create_function_from_string(self.config['TMC-list'][0]['code'])
        self.rule = eval(self.config['TMC-list'][0]['rule'])
        self.assertEqual(self.func(10, 1), True)

    def test_yaml_rule(self):
        self.config = load_yaml("tests/testcases/example.yaml")
        func_name, self.func = create_function_from_string(self.config['TMC-list'][0]['code'])
        self.rule = eval(self.config['TMC-list'][0]['rule'])
        self.assertEqual(self.rule(False), False)

if __name__ == "__main__":
    unittest.main()