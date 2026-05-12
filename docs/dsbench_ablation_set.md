# DSBench Ablation Set

This adds a larger curated DSBench `data_analysis` subset for early TAME ablations without changing the core runner.

## Current Preset

- `ablation_30`

It contains 30 question-level tasks drawn from three workbook-heavy challenges:

- `00000001` `2016-round-1-section-2-chip-off-the-old-block`
- `00000004` `2017-round-1-go-with-the-flow`
- `00000010` `2017-finals-ladder-up`

## Why These Tasks

- They require real spreadsheet-backed computation rather than pure theory MCQs.
- They include mixed answer formats:
  - multiple choice letters
  - integers
  - free-text labels
- Challenge `00000004` adds mixed support files:
  - workbook
  - image
  - csv
- Together they are large enough to make early ablation differences easier to observe than a 10-question pilot.

## Prepare

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.prepare_dsbench_ablation_set \
  --preset ablation_30 \
  --overwrite
```

## Run

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.run_dsbench_pilot \
  --taskset-name dsbench_da_ablation_30 \
  --tame-variant minimal_baseline \
  --max-runs 1 \
  --output-dir results_dsbench/ablation30/minimal
```

## Evaluate

```bash
cd /home/zhoujun/DataSciBench

python -m experiments.evaluate_dsbench_pilot \
  --results-root results_dsbench/ablation30/minimal
```
