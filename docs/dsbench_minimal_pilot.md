# DSBench Minimal Pilot

This is the smallest path to reuse the current `DataSciBench` agent on the `DSBench` data-analysis track without changing the core runner.

## Design

- Keep `experiments/run_examples.py` and the current `SciDataInterpreter` flow unchanged.
- Convert DSBench `data_analysis` questions into standard `DataSciBench/data/<task>/` folders.
- For each DSBench question, copy the challenge support files, challenge introduction, and the current question text.
- Require a single output file:
  - `final_answer.txt`
- Run `minimal_baseline` first so the agent behaves like a thin code-execution baseline.

## Input Mapping

Generated task folders are named like:

- `dsbench_da_00000001_question6`

Each generated folder contains:

- `prompt.json`
- `metadata.json`
- `introduction.txt`
- `<question_name>.txt`
- challenge support files such as `.xlsx`, `.csv`, `.jpg`

## Prompt Mapping

Each DSBench question is converted into a prompt that contains:

- challenge id and name
- challenge introduction
- current question text
- explicit instruction to write only the final answer into `final_answer.txt`

## Recommended TAME Setting

Use `minimal_baseline` first:

- no planning
- no reflection
- no recovery
- single-step code-first behavior

## Prepare 10-task Pilot

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.prepare_dsbench_pilot \
  --limit 10 \
  --overwrite
```

This uses the local DSBench repository at `/home/zhoujun/DSBench` and the bundled `data_analysis/data_old.zip`.

## Run Minimal Baseline

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.run_dsbench_pilot \
  --taskset-name dsbench_da_pilot_10 \
  --tame-variant minimal_baseline \
  --max-runs 1 \
  --output-dir results_dsbench_minimal
```

## Evaluate

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.evaluate_dsbench_pilot \
  --results-root results_dsbench_minimal
```

## Notes

- This pilot currently targets the `data_analysis` track only.
- The local evaluator is heuristic:
  - exact match
  - normalized exact match
  - numeric equivalence for simple scalar answers
- DSBench's official data-analysis evaluation uses an LLM judge for some answers, so this pilot evaluator should be treated as a fast proxy rather than the official score.
