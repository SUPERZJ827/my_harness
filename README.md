# DataSciBench Public Snapshot

This repository is a cleaned public snapshot for running the modified DataSciBench codebase with the local `MetaGPT/` fork.

It is prepared for GitHub upload with these goals:

- keep the runnable code and required local modifications
- avoid uploading local environments and large experiment outputs
- avoid publishing API keys or other secrets
- keep one lightweight sample task so others can verify the pipeline

## Included

- `MetaGPT/`: local modified MetaGPT source used by this project
- `experiments/`, `evaluations/`, `role/`, `src/`, `utils/`
- `metric/`: evaluation configs
- `data/human_0/`: a small sample task for smoke testing
- `tests/`, `docs/`, `test_data/`, `test_excel_files_complex/`

## Not Included In The Public Snapshot

The full benchmark data, large `gt/` artifacts, local virtual environments, and experiment result directories should not be uploaded to GitHub.

For the full benchmark data and evaluation ground truth, use the external dataset referenced by the original project:

- Hugging Face dataset: `https://huggingface.co/datasets/zd21/DataSciBench/tree/main`
- Original project page: `https://github.com/THUDM/DataSciBench`

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install the local MetaGPT package

```bash
cd MetaGPT
pip install .
cd ..
```

### 3. Configure your API key

Create a real config file from the example:

```bash
cp config/config2.example.yaml config/config2.yaml
```

Then edit `config/config2.yaml` and fill in your own key.

Optional: if you also want a local MetaGPT-side copy, create it from:

- `MetaGPT/config/config2.example.local.yaml`

Do not commit real keys to GitHub.

## Minimal Run

Run the included sample task:

```bash
python -m experiments.run_examples --task_id human_0 --max_runs 1 --config config2.yaml --output_dir results
```

## Minimal Evaluation

Evaluate the sample task:

```bash
python -m experiments.evaluate --task_id human_0 --runs_dir results --model_id deepseek-v4-flash
```

## Notes

- `experiments/run_examples.py` adds `MetaGPT/` to `sys.path`, so this repo expects the local modified MetaGPT source tree to exist.
- Large result folders such as `results_*`, `evaluation_results/results`, `venv/`, and `harness/` are intentionally ignored.
- This public snapshot is meant for code sharing and basic reproducibility, not for bundling all local experiment artifacts.
