# DABstep Minimal Pilot

This is the smallest path to reuse the current `DataSciBench` agent on `adyen/DABstep` without rewriting the main runner.

## Design

- Keep the current `run_examples.py` and `SciDataInterpreter` flow unchanged.
- Convert a small DABstep task subset into normal `DataSciBench/data/<task>/` folders.
- Copy the shared DABstep context files into every generated task folder.
- Change the task objective from multi-artifact data analysis to a single answer file:
  - required output: `final_answer.txt`
- Run with `minimal_baseline` first so the agent behaves as a thin code-execution baseline.

## Input Mapping

Generated task folders are named `dabstep_<task_id>`.

Each generated folder contains:

- `prompt.json`
- `metadata.json`
- `payments.csv`
- `fees.json`
- `manual.md`
- `merchant_data.json`
- `merchant_category_codes.csv`
- `acquirer_countries.csv`
- `payments-readme.md`

## Prompt Mapping

Each DABstep row is converted into a prompt that contains:

- task id
- level
- question
- original answer-format guidelines
- explicit instruction to write the final answer only into `final_answer.txt`

This avoids changing the current benchmark harness while still making evaluation deterministic.

## Recommended TAME Setting

Use `minimal_baseline` first:

- no planning
- no reflection
- no recovery
- no artifact contract
- single-step code-first behavior

That gives the closest baseline to a black-box data agent.

## Prepare 10-task Pilot

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.prepare_dabstep_pilot \
  --split dev \
  --level all \
  --limit 10 \
  --overwrite
```

This writes:

- task folders under `data/dabstep_*`
- a manifest file at `experiments/dabstep_task_sets.json`

## Run Minimal Baseline

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.run_examples \
  --task_id "['dabstep_1','dabstep_2']" \
  --tame_variant minimal_baseline \
  --max_runs 1 \
  --output_dir results_dabstep_minimal
```

Replace the task id list with the generated ids printed by the preparation script.

## Evaluate

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.evaluate_dabstep_pilot \
  --results-root results_dabstep_minimal
```

## Notes

- This is a pilot harness, not the official DABstep scorer.
- The evaluation currently uses exact string match and normalized exact match.
- Use the `dev` split first, because it contains ground-truth answers. The `default` split does not provide usable labels for local scoring.
