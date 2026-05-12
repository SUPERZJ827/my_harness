# DSBench Official Eval Adapter

This adapter lets you:

- run DSBench tasks with the existing `DataSciBench` agent and harness
- export the resulting predictions into DSBench's official `save_process/{model}/` layout
- create an isolated workspace that can run copied versions of DSBench's `compute_answer.py` and `show_result.py`

It does not modify any existing `DataSciBench` runner or DSBench repository files.

## What It Creates

Given a results root such as:

- `results_dsbench/a_t`

the adapter creates a workspace like:

- `dsbench_official_eval/a_t/data_analysis/`

Inside that workspace it writes:

- `data.json`
- `data/<challenge_id>/<question>.txt`
- `save_process/<eval_label>/<challenge_id>.json`
- copied and patched `compute_answer.py`
- copied and patched `show_result.py`

The copied scripts are patched only inside the isolated workspace so they:

- read `OPENAI_API_KEY` from the environment
- point to your exported `save_process/<eval_label>/`

## Export Only

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.export_dsbench_official_eval \
  --results-root /home/zhoujun/DataSciBench/results_dsbench/a_t
```

## Export And Run Official Judge

```bash
cd /home/zhoujun/DataSciBench

OPENAI_API_KEY=your_key \
python -m experiments.export_dsbench_official_eval \
  --results-root /home/zhoujun/DataSciBench/results_dsbench/a_t \
  --run-official-judge
```

## Notes

- This adapter currently targets the DSBench `data_analysis` track.
- It supports partial pilots. The generated `data.json` is filtered to only the challenge/question subset present in the exported results.
- The official judge uses an LLM, so results may differ slightly from the local heuristic evaluator.
