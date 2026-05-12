import unittest
from src.utils import json_data_to_yaml

class TestUtils(unittest.TestCase):
    def test_json_to_yaml(self):
        json_data = {"name": "John", "age": 30}
        expected_yaml = 'age: 30\nname: John\n'

        result = json_data_to_yaml(json_data, "tests/test_outputs/test.yaml")
        self.assertEqual(result, expected_yaml)

if __name__ == "__main__":
    unittest.main()