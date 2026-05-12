import json
import yaml
import os
import sys
from contextlib import contextmanager


def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def list_to_dict_by_task(data_list: list):
    return {item['metric']: item for item in data_list}


def create_function_from_string(func_str):
    local_vars = {}
    exec(func_str, globals(), local_vars)
    
    # Extract the function name from the function body if needed
    # Here assuming function definition is 'def <name>...'
    for name, obj in local_vars.items():
        if callable(obj):
            return name, obj
    return None, None


def json_data_to_yaml(json_data: dict, yaml_file_path: str):
    """
    Transforms a JSON data to a YAML data file

    Args:
        - json_data (dict): The JSON data
    """
    # Write the data to a YAML file
    yaml_data = yaml.dump(json_data, default_flow_style=False)

    with open(yaml_file_path, 'w') as file:
        file.write(yaml_data)

    return yaml_data


@contextmanager
def change_dir(new_dir):
    """Temporarily change the working directory."""
    current_dir = os.getcwd()  # Save the current working directory
    try:
        os.chdir(new_dir)  # Change to the new directory
        yield
    finally:
        os.chdir(current_dir)  # Change back to the original directory

@contextmanager
def change_metalog_path(logger=None, file_path: str = None, print_level="DEBUG", logfile_level="DEBUG"):
    """
    Permanantly change the log file path of the logger.
    """
    try:
        logger.remove()
        logger.add(sys.stderr, level=print_level)
        logger.add(file_path, level=logfile_level)
        yield logger
    finally:
        logger.remove()