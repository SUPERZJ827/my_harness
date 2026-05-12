# Local Modifications Relative to the Original Repository

This project is based on the original DataSciBench repository and a locally modified MetaGPT fork.

This document summarizes the main engineering changes made in this version. It is intended as a structural overview, not as a full line-by-line diff.

## 1. TAME-style execution variants were added

New files:

- `role/tame_config.py`
- `role/tame_artifacts.py`
- `role/tame_recovery.py`
- `role/tame_runtime_state.py`

Main purpose:

- introduce configurable TAME variants such as `full_tame`, `baseline_a_t_plus`, `wo_t_plus`, and related ablations
- expose switches for planning, reflection, retry, recovery, artifact tracking, final guard, and step budget
- make it possible to run systematic ablation experiments without rewriting the core runner

## 2. The main generation runner was extended significantly

Main file:

- `experiments/run_examples.py`

Key changes:

- adds TAME variant selection via `--tame_variant`
- supports `--max_retry`, `--tame_max_steps`, `--task-timeout-seconds`, `--list_tame_variants`
- stages task input files into the run directory automatically before execution
- injects task-specific artifact contracts derived from `metric/<task_id>/metric.yaml`
- normalizes special-case task inputs such as `csv_excel_48`
- supports DSBench-specific task handling through an adapter layer
- writes outputs into a more structured run directory format such as:
  - `<output_dir>/<task_id>/<model>__<variant>_<run_index>/`

## 3. Artifact-aware prompting and checking were added

Main file:

- `role/tame_artifacts.py`

What changed:

- evaluation configs are parsed to infer required output artifact names and expected columns
- these artifact requirements are turned into a prompt contract and injected into generation
- the goal is to reduce failures caused by missing files, wrong filenames, or wrong CSV column names

## 4. The local SciDataInterpreter flow was customized

Main file:

- `role/sci_data_interpreter.py`

Related MetaGPT modifications:

- `MetaGPT/metagpt/actions/di/write_analysis_code.py`
- `MetaGPT/metagpt/actions/di/write_plan.py`
- `MetaGPT/metagpt/prompts/di/write_analysis_code.py`
- `MetaGPT/metagpt/provider/openai_api.py`
- `MetaGPT/metagpt/roles/di/data_interpreter.py`
- `MetaGPT/metagpt/strategy/planner.py`

High-level effect:

- the upstream Data Interpreter behavior was adapted to support the local TAME workflow
- planning, execution, retry, and logging behavior were adjusted for benchmark-style runs
- the MetaGPT prompt and execution stack was modified to better match this repository’s task format and experiment structure

## 5. DSBench support was added on top of the original DataSciBench runner

Main files:

- `experiments/dsbench_adapter.py`
- `experiments/prepare_dsbench_pilot.py`
- `experiments/run_dsbench_pilot.py`
- `experiments/evaluate_dsbench_pilot.py`
- `experiments/evaluate_dsbench_batch.py`
- `experiments/export_dsbench_official_eval.py`
- `docs/dsbench_official_eval_adapter.md`

What this adds:

- support for `dsbench_da_*` style tasks inside the existing runner
- helper files such as workbook summaries and CSV profiles for spreadsheet-heavy tasks
- normalization of `final_answer.txt` for DSBench answer formats
- export into DSBench’s official evaluation layout
- optional execution of the official DSBench judge in an isolated workspace

## 6. DABStep support and pilot preparation utilities were added

Main files:

- `experiments/prepare_dabstep_pilot.py`
- `experiments/run_dabstep_pilot.py`
- `experiments/evaluate_dabstep_pilot.py`
- `experiments/dabstep_task_sets.json`
- `docs/dabstep_minimal_pilot.md`

What changed:

- adds tooling to prepare, run, and evaluate DABStep-style pilot task sets
- allows this repository to be used for cross-benchmark pilot experiments rather than only the original DataSciBench task pool

## 7. Additional experiment-management and ablation tooling was added

Main files:

- `experiments/prepare_dsbench_ablation_set.py`
- `experiments/evaluate_data_analysis_metrics.py`
- `experiments/summarize_data_analysis_ablation.py`
- `experiments/evaluate_bcb_from_runs.py`
- `experiments/dsbench_task_sets.json`
- `experiments/tame_task_sets.json`

What this adds:

- utilities for building task subsets
- utilities for data-analysis-focused ablation evaluation
- utilities for summary table generation
- utilities for batch evaluation across result roots

## 8. Evaluation behavior was extended and made more flexible

Main files:

- `experiments/evaluate.py`
- `evaluations/check_result.py`
- `evaluation_results/calculate_final_metric.py`

Key changes:

- task selection now supports single ids, comma-separated ids, Python-style list strings, `all`, `original_55`, and `original_full`
- evaluation can optionally skip VLM-based metrics via `--skip_vlm`
- result scanning is more flexible with custom `--runs_dir`
- progress checking was updated to align with the newer run directory organization

## 9. Configuration loading and logging were made more robust

Main file:

- `src/logs.py`

What changed:

- config path resolution now checks multiple locations
- logger creation was adapted to the structured results layout
- result logs and time logs are separated more clearly

## 10. Task prompts and metric files were revised in many places

Affected areas:

- multiple `data/*/prompt.json`
- multiple `metric/*/metric.yaml`

Purpose:

- align prompts, expected outputs, and evaluation rules with the modified execution pipeline
- support ablation studies, DSBench integration, and task-specific artifact contracts

## 11. Tool schema files inside MetaGPT were updated

Affected files:

- multiple files under `MetaGPT/tools/schemas/`

Purpose:

- align tool recommendations and tool-use metadata with this repository’s local benchmark workflow

## 12. Public-release cleanup and documentation were added

Main files:

- `README.md`
- `README_ZH.md`
- `docs/github_upload_guide.md`

What changed:

- this public snapshot was reorganized so that users can clone and run a lightweight sample without your full local experiment outputs
- example config files are provided instead of committed real runtime secrets
- the README now includes environment setup, command reference, dataset import guidance, and troubleshooting

## Suggested short description for external users

If you need a short explanation in a README or project page, this version can be described as:

> A locally extended DataSciBench fork with a modified MetaGPT runtime, TAME-style execution variants, DSBench/DABStep pilot support, improved artifact-aware prompting, and additional evaluation/ablation tooling.

## Important note

This document is a high-level summary of the main local modifications. It should be treated as an overview of engineering intent and major feature additions, not as an exhaustive upstream comparison.
