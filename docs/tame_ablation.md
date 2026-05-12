# TAME Ablation Harness

This repository now exposes DataSciBench runs as TAME variants over the existing
`SciDataInterpreter` thin harness.

## Variants

Use `--tame_variant` with one of:

- `minimal_baseline`
- `baseline_a`
- `baseline_m`
- `baseline_t_plus`
- `baseline_a_m`
- `baseline_a_t_plus`
- `baseline_m_t_plus`
- `full_tame`
- `wo_a_reflection`
- `wo_m_recovery`
- `wo_t_plus`

`E_core` is always enabled because DataSciBench needs code generation and
execution artifacts.

## Layer Controls

- `T_min`: always enabled through the thin task contract prompt.
- `T_plus`: enables the stronger governance prompt, code verifier, and step budget.
- `A`: controls explicit planning, reflection, working memory, task-context reuse, and data checks.
- `M`: controls checkpointing, runtime ledger, resume state, and recovery-oriented retries.
- `E_core`: uses the existing notebook-based Python executor.

## Commands

List variants:

```bash
python -m experiments.run_examples --list_tame_variants
```

Run one task with Full TAME:

```bash
python -m experiments.run_examples --task_id human_22 --data_type human --config test_config.yaml --tame_variant full_tame
```

Run the minimal baseline:

```bash
python -m experiments.run_examples --task_id human_22 --data_type human --config test_config.yaml --tame_variant minimal_baseline
```

Override T_plus step budget:

```bash
python -m experiments.run_examples --task_id human_22 --data_type human --config test_config.yaml --tame_variant full_tame --tame_max_steps 10
```

Override retry count:

```bash
python -m experiments.run_examples --task_id human_22 --data_type human --config test_config.yaml --tame_variant baseline_a --max_retry 1
```

## Outputs

Runs are stored under:

```text
results/<task_id>/<model>__<tame_variant>_<run_id>/
```

When M checkpointing is enabled, the run directory also contains:

- `tame_checkpoint.json`
- `tame_ledger.jsonl`

The output JSONL includes:

- `tame_variant`
- `tame_layers`
- the original DataSciBench plan/cost/error fields
