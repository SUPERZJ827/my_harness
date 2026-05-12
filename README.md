# DataSciBench Public Snapshot

Chinese version: [README_ZH.md](README_ZH.md)

Local modifications summary: [docs/local_modifications.md](docs/local_modifications.md)

This repository is a cleaned public snapshot of a modified `DataSciBench + MetaGPT` workflow.

The goal of this public version is simple:

- let other users clone the repository and understand how to run it
- keep the core code and local MetaGPT modifications
- remove large local experiment outputs and local environments
- avoid publishing real API keys

This public snapshot currently includes one lightweight sample task, `data/human_0`, so new users can verify the pipeline without downloading the full benchmark first.

## What is in this repo

- `MetaGPT/`: the local modified MetaGPT source used by this project
- `experiments/`: run scripts and benchmark preparation scripts
- `evaluations/`: progress-check scripts and shell helpers
- `role/`, `src/`, `utils/`: core project logic
- `metric/`: evaluation configs
- `data/human_0/`: a small sample task for smoke testing
- `docs/`: notes and experiment writeups

## What is intentionally not included

This repo does not bundle the full benchmark dataset, large `gt/` artifacts, local virtual environments, or your local result directories such as `results_*`.

For the full benchmark data and the original project context:

- Original project: `https://github.com/THUDM/DataSciBench`
- Evaluation data: `https://huggingface.co/datasets/zd21/DataSciBench/tree/main`

## Recommended environment

- OS: Linux is recommended
- Python: `3.10` is recommended for consistency with the local project environment
- Minimum Python supported by MetaGPT setup: `>=3.9`

## Repository layout

The main directories a new user should care about are:

- `experiments/run_examples.py`: main generation entrypoint
- `experiments/evaluate.py`: main evaluation entrypoint
- `evaluations/check_result.py`: generation progress checker
- `config/config2.example.yaml`: example model config
- `data/human_0/`: included sample task
- `metric/human_0/metric.yaml`: metric config for the sample task

## Complete setup

### 1. Clone the repo

```bash
git clone https://github.com/SUPERZJ827/my_harness.git
cd my_harness
```

### 2. Create a Python environment

Using `venv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Install project dependencies

```bash
pip install -r requirements.txt
```

### 4. Install the local MetaGPT fork from this repository

This project uses the local `MetaGPT/` source tree, not a random external install.

```bash
cd MetaGPT
pip install .
cd ..
```

### 5. Create the runtime config file

Copy the example config:

```bash
cp config/config2.example.yaml config/config2.yaml
```

Then edit `config/config2.yaml` and fill in your own model settings:

```yaml
llm:
  api_type: "openai"
  model: "deepseek-v4-flash"
  base_url: "https://api.deepseek.com/v1"
  api_key: "YOUR_API_KEY"
```

Notes:

- `api_key` must be replaced with your real key.
- Do not commit `config/config2.yaml`.
- The repo only tracks the example file.

Optional: if you also want a separate MetaGPT-side local example, this repo also includes:

- `MetaGPT/config/config2.example.local.yaml`

### 6. Understand how `--config` is resolved

When you pass `--config config2.yaml`, the code searches in roughly this order:

1. `MetaGPT/config/config2.yaml`
2. `MetaGPT/config2.yaml`
3. `config/config2.yaml`
4. MetaGPT home config directory
5. project root
6. current working directory

For normal use in this public repo, the intended file is:

- `config/config2.yaml`

## Fastest possible smoke test

This is the lowest-friction way for a new user to verify that the pipeline is wired correctly.

### Run the included sample task

```bash
python -m experiments.run_examples \
  --task_id human_0 \
  --max_runs 1 \
  --config config2.yaml \
  --output_dir results
```

### Evaluate the sample task

Use the model name from your config file. For example, if the config says `deepseek-v4-flash`:

```bash
python -m experiments.evaluate \
  --task_id human_0 \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

### Check generation progress

```bash
python -m evaluations.check_result \
  --model_id deepseek-v4-flash \
  --runs_dir results
```

## Expected output structure

After a run, results are usually written under:

```text
results/<task_id>/<model_name>__<tame_variant>_<run_index>/
```

For example:

```text
results/human_0/deepseek-v4-flash__full_tame_0/
```

Typical files inside a run directory:

- `logs.txt`
- `sys_logs.txt`
- generated task artifacts

There may also be an aggregated output file like:

```text
results/human_0/deepseek-v4-flash__full_tame_outputs.jsonl
```

## Data preparation and ground-truth layout

This is the part that usually causes the most confusion.

In this project, a runnable task is not just a prompt. A task normally needs three things:

1. a task folder under `data/`
2. a matching metric folder under `metric/`
3. ground-truth files under `data/<task_id>/gt/`

### Minimal directory contract for one task

For a task called `human_0`, the expected layout is:

```text
data/
  human_0/
    prompt.json
    data.csv                  # optional, if the task needs input files
    other_input_file.ext      # optional
    gt/
      expected_output.ext
      test_gt.py              # optional, depends on the task

metric/
  human_0/
    metric.yaml
```

### What each file is for

`data/<task_id>/prompt.json`
: The task definition. This is required. It contains at least the task prompt, and often also a `data_source_type` field used for filtering.

`data/<task_id>/...`
: The input files that will be staged into the run directory before generation starts. These can be `.csv`, `.xlsx`, `.xls`, `.json`, `.txt`, `.md`, `.parquet`, image files, `.npy`, `.pkl`, `.h5`, `.pth`, and a few other supported formats.

`data/<task_id>/gt/`
: The ground-truth directory used during evaluation.

`metric/<task_id>/metric.yaml`
: The evaluation config that tells the evaluator what checks to run and which files inside `gt/` should be treated as ground truth.

### How ground-truth resolution works

During evaluation, the code treats:

```text
data/<task_id>/gt/
```

as the base ground-truth directory.

Then each metric entry in `metric/<task_id>/metric.yaml` can point to a file relative to that directory.

For example, if `metric.yaml` contains:

```yaml
ground_truth: most_corr_output.csv
```

then the evaluator will resolve it as:

```text
data/human_0/gt/most_corr_output.csv
```

So the practical rule is:

- put real reference outputs inside `data/<task_id>/gt/`
- in `metric.yaml`, write paths relative to `gt/`

### Concrete example from the included sample task

The sample task in this repo is:

```text
data/human_0/
  prompt.json
  data.csv
  gt/
    most_corr_output.csv
    test_gt.py

metric/human_0/
  metric.yaml
```

The corresponding `metric.yaml` references:

```yaml
ground_truth: most_corr_output.csv
```

which means evaluation will read:

```text
data/human_0/gt/most_corr_output.csv
```

### Required files for different use cases

Case 1: prompt-only task with no external input files

Minimum:

```text
data/<task_id>/prompt.json
data/<task_id>/gt/<expected_output>
metric/<task_id>/metric.yaml
```

Case 2: task with input files such as CSV / Excel

Minimum:

```text
data/<task_id>/prompt.json
data/<task_id>/input_file.csv
data/<task_id>/gt/<expected_output>
metric/<task_id>/metric.yaml
```

Case 3: task with custom evaluation code

Often includes:

```text
data/<task_id>/gt/test_gt.py
metric/<task_id>/metric.yaml
```

### How to prepare more tasks manually

If you want to extend this public snapshot with more tasks, the safest workflow is:

1. create `data/<task_id>/`
2. place `prompt.json` there
3. place all required input files in the same task directory
4. create `data/<task_id>/gt/`
5. place the expected output files used by evaluation inside `gt/`
6. create `metric/<task_id>/metric.yaml`
7. make sure every `ground_truth:` entry in `metric.yaml` points to a file relative to `data/<task_id>/gt/`

### How to import the full benchmark dataset

This public repo does not ship the full dataset. If you download the full benchmark yourself, your goal is to reconstruct the same logical structure:

```text
data/<task_id>/...
metric/<task_id>/metric.yaml
data/<task_id>/gt/...
```

In practice:

1. download the original benchmark task folders
2. copy each task folder into `data/`
3. ensure the corresponding metric folder exists under `metric/`
4. ensure each task has a usable `gt/` directory

### Practical import workflow

If you want a more operational checklist, use this process.

Step 1: download the original task data

- Download the benchmark task folders to a temporary directory first.
- Do not immediately mix them into this repo before checking the layout.

Step 2: inspect the downloaded folder structure

Ideally the downloaded content already looks like:

```text
<download_root>/
  human_0/
  human_1/
  csv_excel_0/
  dl_0/
  ...
```

For each task folder, verify at least:

- `prompt.json` exists
- input files such as `.csv`, `.xlsx`, `.json` exist when needed
- `gt/` exists if the downloaded package already includes ground truth

Step 3: copy task folders into `data/`

After checking the layout, copy each task folder into:

```text
data/<task_id>/
```

Step 4: verify `metric/` has matching task ids

For every task you want to run, confirm:

```text
metric/<task_id>/metric.yaml
```

exists.

Step 5: verify each task has `gt/`

For every imported task, check:

```text
data/<task_id>/gt/
```

If `gt/` is missing, generation may still run, but evaluation will not work correctly until the ground-truth files are added.

Step 6: validate one task before validating the whole dataset

Before launching a large run, pick one imported task and confirm:

- `data/<task_id>/prompt.json` exists
- required input files are present
- `metric/<task_id>/metric.yaml` exists
- `data/<task_id>/gt/` exists

Step 7: run a single-task smoke test

Example:

```bash
python -m experiments.run_examples \
  --task_id human_1 \
  --max_runs 1 \
  --config config2.yaml \
  --output_dir results_import_check
```

Then evaluate it:

```bash
python -m experiments.evaluate \
  --task_id human_1 \
  --runs_dir results_import_check \
  --model_id deepseek-v4-flash
```

If one imported task works end to end, the rest of the dataset usually follows the same structure.

### Suggested shell checks after importing data

Count task folders under `data/`:

```bash
find data -mindepth 1 -maxdepth 1 -type d | wc -l
```

Count metric folders:

```bash
find metric -mindepth 1 -maxdepth 1 -type d | wc -l
```

Check which data tasks do not have matching metric folders:

```bash
for d in data/*; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  [ -f "metric/$name/metric.yaml" ] || echo "missing metric: $name"
done
```

Check which tasks are missing `gt/`:

```bash
for d in data/*; do
  [ -d "$d" ] || continue
  [ -d "$d/gt" ] || echo "missing gt: $(basename "$d")"
done
```

Check which tasks are missing `prompt.json`:

```bash
for d in data/*; do
  [ -d "$d" ] || continue
  [ -f "$d/prompt.json" ] || echo "missing prompt: $(basename "$d")"
done
```

### If the downloaded dataset does not already contain `gt/`

In that case, you need to reconstruct the evaluation layout manually:

1. create `data/<task_id>/gt/`
2. place the expected reference output files inside it
3. update `metric/<task_id>/metric.yaml` so each `ground_truth:` entry points to the correct file relative to `gt/`

Example:

```text
data/human_8/gt/final_report.csv
metric/human_8/metric.yaml
```

and inside `metric.yaml`:

```yaml
ground_truth: final_report.csv
```

### If the downloaded dataset contains nested duplicate `gt/gt/`

Some local snapshots may contain both:

```text
data/<task_id>/gt/
data/<task_id>/gt/gt/
```

For this project, the evaluator uses:

```text
data/<task_id>/gt/
```

as the base directory.

So the safer convention is:

- keep the actual reference files directly under `data/<task_id>/gt/`
- avoid depending on `gt/gt/` unless you intentionally changed `metric.yaml` paths to match it

### Common data-preparation mistakes

Mistake 1:

- putting the reference output under `data/<task_id>/` instead of `data/<task_id>/gt/`

Mistake 2:

- writing an absolute path in `metric.yaml` instead of a path relative to `gt/`

Mistake 3:

- copying the prompt but forgetting the input data files

Mistake 4:

- having `data/<task_id>/` but no matching `metric/<task_id>/metric.yaml`

Mistake 5:

- using a task id under `data/` that does not exactly match the folder name under `metric/`

## Main command reference

### 1. Generation: `python -m experiments.run_examples`

This is the main script for running tasks.

Basic form:

```bash
python -m experiments.run_examples --config config2.yaml
```

Useful examples:

Run one sample task once:

```bash
python -m experiments.run_examples \
  --task_id human_0 \
  --max_runs 1 \
  --config config2.yaml \
  --output_dir results
```

Run all included `human_*` tasks:

```bash
python -m experiments.run_examples \
  --data_type human \
  --config config2.yaml \
  --output_dir results
```

Run a predefined 55-task set:

```bash
python -m experiments.run_examples \
  --task_id original_55 \
  --max_runs 1 \
  --config config2.yaml \
  --output_dir results
```

Run with a different TAME variant:

```bash
python -m experiments.run_examples \
  --task_id human_0 \
  --max_runs 1 \
  --tame_variant baseline_a_t_plus \
  --config config2.yaml \
  --output_dir results
```

Run with a task timeout:

```bash
python -m experiments.run_examples \
  --task_id human_0 \
  --max_runs 1 \
  --task-timeout-seconds 900 \
  --config config2.yaml \
  --output_dir results
```

List supported TAME variants:

```bash
python -m experiments.run_examples --list_tame_variants
```

High-parameter example close to a real experiment run:

```bash
python -m experiments.run_examples \
  --task_id original_55 \
  --max_runs 3 \
  --data_type all \
  --output_dir results_55tasks \
  --tame_variant full_tame \
  --max_retry 3 \
  --tame_max_steps 20 \
  --task-timeout-seconds 1800 \
  --use_reflection \
  --hard_retry \
  --config config2.yaml
```

What this command does:

- runs the predefined `original_55` task set
- repeats each task 3 times
- writes results under `results_55tasks/`
- uses the `full_tame` preset
- enables reflection and hard retry
- overrides retry count and T+ step budget
- aborts a single task if it exceeds 1800 seconds

If you want a react-style variant of the same run, add:

```bash
--use_react
```

#### Parameters for `experiments.run_examples`

`--task_id`
: Task id to run. Examples: `human_0`, `dl_0`, `original_55`. If omitted, the script scans the `data/` directory.

`--data_source_type`
: Filter tasks by `prompt.json["data_source_type"]`. Only needed for selective dataset runs.

`--max_runs`
: Number of repeated runs per task. Default: `3`.

`--gt_prompt`
: Prepends a custom prompt prefix before the task prompt.

`--continue_gen`
: Continue a previous generation instead of skipping existing logs.

`--output_dir`
: Root directory for generated results. Default: `results`.

`--data_type`
: Coarse task-type filter. Default: `human`. Common values: `human`, `dl`, `bcb`, `csv`, `all`.

`--skip_bcb`
: Skip BigCodeBench tasks even if they are present in `data/`.

`--use_reflection`
: Enables reflection-related behavior in the TAME config.

`--hard_retry`
: Enables hard retry behavior inside the role runtime.

`--max_retry`
: Override the TAME retry limit.

`--use_react`
: Switch from plan-and-act style to react-style execution.

`--tame_variant`
: TAME preset name. Default: `full_tame`.

`--tame_max_steps`
: Override the T+ execution budget.

`--task-timeout-seconds`
: Optional wall-clock timeout per task.

`--list_tame_variants`
: Print supported TAME variants and exit.

`--config`
: Config file name or path. Default in code is `test_config.yaml`, but for this public repo you should normally pass `--config config2.yaml`.

### 2. Evaluation: `python -m experiments.evaluate`

This script reads generated run directories and evaluates them against `metric/<task_id>/metric.yaml`.

Basic form:

```bash
python -m experiments.evaluate \
  --task_id human_0 \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

Useful examples:

Evaluate one task:

```bash
python -m experiments.evaluate \
  --task_id human_0 \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

Evaluate multiple tasks:

```bash
python -m experiments.evaluate \
  --task_id human_0,human_1,human_2 \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

Evaluate all tasks currently present under `data/`:

```bash
python -m experiments.evaluate \
  --task_id all \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

Skip VLM-based evaluation metrics:

```bash
python -m experiments.evaluate \
  --task_id human_0 \
  --runs_dir results \
  --model_id deepseek-v4-flash \
  --skip_vlm
```

Matching evaluation command for the high-parameter run above:

```bash
python -m experiments.evaluate \
  --task_id original_55 \
  --runs_dir results_55tasks \
  --model_id deepseek-v4-flash \
  --skip_vlm
```

#### Parameters for `experiments.evaluate`

`--requirement`
: Internal/debug field. Usually leave empty.

`--plan`
: Internal/debug field. Usually leave empty.

`--metric_path`
: Optional explicit metric path. Usually not needed because the script resolves `metric/<task_id>/metric.yaml`.

`--debug_mode`
: Include debug or special runs when scanning output directories.

`--task_id`
: Task selector. Supports:
- single id, for example `human_0`
- comma-separated ids, for example `human_0,human_1`
- Python-style list string, for example `"[\"human_0\", \"human_1\"]"`
- `all`
- `original_55`
- `original_full`

`--model_id`
: Model name prefix used to match result directories. This should usually match the `llm.model` field in your config.

`--runs_dir`
: Root results directory to read from. Default: `results`.

`--skip_vlm`
: Exclude VLM/API-based evaluators from CR computation.

`--include_bcb`
: Include BCB tasks during evaluation.

Evaluation output is written to:

```text
evaluation_results/<model_name>_results.csv
```

### 3. Progress check: `python -m evaluations.check_result`

This script gives a quick overview of how many tasks completed and how many produced valid logs.

Example:

```bash
python -m evaluations.check_result \
  --model_id deepseek-v4-flash \
  --runs_dir results
```

Parameters:

`--model_id`
: Model id to inspect, or `all`.

`--runs_dir`
: Root results directory to inspect. Default: `results`.

## Supported TAME variants

The repo currently supports these variant names:

- `minimal_baseline`
- `baseline_a`
- `baseline_m`
- `baseline_m_final_guard`
- `baseline_t_plus`
- `baseline_a_m`
- `baseline_a_t_plus`
- `baseline_a_t_recovery_only`
- `baseline_a_t_final_guard`
- `baseline_m_t_plus`
- `full_tame`
- `full_tame_final_guard`
- `wo_a_reflection`
- `wo_a_reflection_final_guard`
- `wo_m_recovery`
- `wo_m_recovery_final_guard`
- `wo_t_plus`
- `wo_t_plus_final_guard`

The default is:

- `full_tame`

If you are unsure what to use, start with `full_tame`.

## How to add the full benchmark data later

This public snapshot keeps only `data/human_0/` for easy onboarding.

If you want to run more tasks:

1. download the full benchmark data from the original dataset source
2. place task directories under `data/`
3. make sure matching metric directories exist under `metric/`
4. rerun the same commands with a broader `--task_id` or `--data_type`

## Common pitfalls

### 1. The script cannot find `config2.yaml`

Cause:

- you copied only the example file but did not create the real runtime config

Fix:

```bash
cp config/config2.example.yaml config/config2.yaml
```

### 2. The run starts but evaluation finds no matching runs

Cause:

- `--model_id` does not match the model name in `config/config2.yaml`

Fix:

- use the same model string in both generation and evaluation
- for example, if config contains `deepseek-v4-flash`, then use `--model_id deepseek-v4-flash`

### 3. A task is skipped unexpectedly

Common causes:

- `--data_type` filtered it out
- previous logs already exist and `--continue_gen` was not set
- the task folder does not have a readable `prompt.json`

### 4. Full benchmark tasks are missing

That is expected in this public snapshot. Only a lightweight sample task is included by design.

## Minimal workflow summary

If a user wants the shortest copy-paste path:

```bash
git clone https://github.com/SUPERZJ827/my_harness.git
cd my_harness
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cd MetaGPT && pip install . && cd ..
cp config/config2.example.yaml config/config2.yaml
```

Edit `config/config2.yaml`, then run:

```bash
python -m experiments.run_examples --task_id human_0 --max_runs 1 --config config2.yaml --output_dir results
python -m experiments.evaluate --task_id human_0 --runs_dir results --model_id deepseek-v4-flash
python -m evaluations.check_result --model_id deepseek-v4-flash --runs_dir results
```
