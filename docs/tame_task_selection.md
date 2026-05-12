# TAME Task Selection

The TAME ablation should not be evaluated only on short single-pass cleaning
tasks. The recommended subsets below prefer tasks that stress at least one of:

- Multi-step dependency chains across generated artifacts.
- Modeling/training/evaluation loops where retry and reflection matter.
- Multiple input files or non-trivial input staging.
- Visualization/report/model artifact generation.
- Many required output files, making task governance and progress tracking useful.

## Recommended 10-Task Sanity Set

Use this for cheap first comparisons across variants.

| Task | Why it is useful |
| --- | --- |
| `human_22` | Simple baseline check for file staging and sequential preprocessing. |
| `csv_excel_39` | 11 deterministic sub-outputs; good for T/task-contract and artifact completeness. |
| `csv_excel_32` | Preprocessing + neural model + cross-validation + nested `results/final_results.txt`. |
| `csv_excel_2` | STFT + filtering + CNN pipeline; stresses planning and generated intermediate files. |
| `csv_excel_48` | Train/test classification with preprocessing, model artifact, and evaluation metrics. |
| `human_8` | Multi-file dataset, clustering, association rules, visualizations, final report. |
| `human_12` | Adult dataset cleaning, model checkpoint, clustering, PDF report. |
| `human_7` | Excel input, visualization, Apriori mining, business report. |
| `dl_15` | PyTorch model definition, training, pruning, fine-tuning, multiple model artifacts. |
| `dl_31` | Text data parsing, CNN modeling, PDF/model/evaluation/prediction outputs. |

## Recommended 20-Task Broad Set

Use this after the 10-task set is stable.

```text
human_22
csv_excel_39
csv_excel_32
csv_excel_2
csv_excel_48
human_8
human_12
human_7
dl_15
dl_31
dl_0
dl_9
dl_16
human_10
human_11
human_17
human_5
csv_excel_33
csv_excel_4
human_24
```

## Layer Expectations

- `T_plus` should help most on `csv_excel_39`, `human_8`, `human_12`, and `dl_0`, where many artifacts must be named exactly and task boundaries matter.
- `A` should help most on `csv_excel_2`, `csv_excel_32`, `csv_excel_48`, `dl_15`, `dl_31`, and `dl_9`, where decomposition, modeling choices, and error-aware rewriting matter.
- `M` should help most on `dl_0`, `dl_15`, `human_8`, and `human_12`, where runs are long and many intermediate outputs can be checkpointed.
- `A+M` synergy should be visible on long pipelines with model artifacts and reports, especially `dl_0`, `dl_15`, `human_8`, and `human_12`.

## Known Risks

- Some metrics are strict about exact CSV formatting and may understate semantically correct outputs.
- A few metric files have fragile code paths; inspect failures before treating CR as definitive.
- Deep learning tasks can be slow. Use `--tame_max_steps` and `--max_runs 1` for initial smoke tests.

## Example Commands

Run the 10-task set by passing the Python list string to `--task_id`:

```bash
python -m experiments.run_examples --task_id "['human_22','csv_excel_39','csv_excel_32','csv_excel_2','csv_excel_48','human_8','human_12','human_7','dl_15','dl_31']" --data_type "" --config config2.yaml --tame_variant minimal_baseline --max_runs 1 --output_dir results_minimal_10
```

Run Full TAME on the same set:

```bash
python -m experiments.run_examples --task_id "['human_22','csv_excel_39','csv_excel_32','csv_excel_2','csv_excel_48','human_8','human_12','human_7','dl_15','dl_31']" --data_type "" --config config2.yaml --tame_variant full_tame --max_runs 1 --output_dir results_full_10
```
