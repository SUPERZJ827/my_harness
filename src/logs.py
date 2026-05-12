import logging
import argparse
import os
from pathlib import Path
import yaml
from metagpt.const import CONFIG_ROOT

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_config_path(config_name="config2.yaml"):
    config_name = config_name or "config2.yaml"
    candidates = []
    config_path = Path(config_name).expanduser()
    if config_path.is_absolute() or config_path.parent != Path("."):
        candidates.append(config_path)
    else:
        candidates.extend(
            [
                PROJECT_ROOT / "MetaGPT" / "config" / config_name,
                PROJECT_ROOT / "MetaGPT" / config_name,
                PROJECT_ROOT / "config" / config_name,
                CONFIG_ROOT / config_name,
                PROJECT_ROOT / config_name,
                Path.cwd() / config_name,
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"Config file '{config_name}' was not found. Searched: {searched}")


def get_model_name(config_name="config2.yaml"):
    config_name = config_name or "config2.yaml"
    print("Config Root: ", CONFIG_ROOT)
    print("Config Name: ", config_name)
    config_path = resolve_config_path(config_name)
    # Load the config file
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Get the model name from the config
    model_name = config["llm"]["model"]

    return model_name

def create_logger(id, sub_idx=None, target_dir=None, config_name=None, split=True, output_root="results"):
    # Create the log directory if it doesn't exist
    if split:
        model_name = get_model_name(config_name).split('/')[-1]
    else:
        model_name = get_model_name(config_name)
    if sub_idx is not None:
        log_dir = os.path.join(output_root, str(id), model_name+f"_{sub_idx}")
        run_dir = os.path.join(output_root, str(id))
        os.makedirs(log_dir, exist_ok=True)
        time_log_file = os.path.join("logs", model_name+f"_{sub_idx}_time.txt")
    else:
        log_dir = os.path.join(output_root, str(id), model_name)
        run_dir = os.path.join(output_root, str(id))
        os.makedirs(log_dir, exist_ok=True)
        time_log_file = os.path.join("logs", model_name+"_time.txt")

    if target_dir is not None:
        log_dir = os.path.join(output_root, str(id), target_dir)
        run_dir = os.path.join(output_root, str(id))
        os.makedirs(log_dir, exist_ok=True)
        time_log_file = os.path.join("logs", target_dir+"_time.txt")

    # Create a logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create a file handler and set the log file path
    log_file = os.path.join(log_dir, "logs.txt")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # Create a formatter and add it to the file handler
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    if logger.hasHandlers():
        logger.handlers.clear()
    # Add the file handler to the logger
    logger.addHandler(file_handler)

    # ===================================================
    # Create the time logger below
    # ===================================================

    time_logger = logging.getLogger(f"time_logger")
    time_logger.setLevel(logging.INFO)

    # Create a file handler for the time log
    time_file_handler = logging.FileHandler(time_log_file)
    time_file_handler.setLevel(logging.INFO)

    # Use a simple formatter for the time log
    time_formatter = logging.Formatter('%(asctime)s - %(message)s')
    time_file_handler.setFormatter(time_formatter)

    # Clear existing handlers and add the new time file handler
    if time_logger.hasHandlers():
        time_logger.handlers.clear()
    time_logger.addHandler(time_file_handler)

    return logger, time_logger, log_dir, run_dir

if __name__ == "__main__":
    logger = create_logger(0)
    logger.info("Logger created")
