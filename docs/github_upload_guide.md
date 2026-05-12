# GitHub Upload Guide

This project should be uploaded to a new GitHub repository as a fresh repo, not by pushing the current local Git history directly.

Reason:

- the current working directory contains old Git history
- local environment files were tracked before
- local experiment outputs and temporary files are mixed into the workspace

## Recommended Approach

Create a clean export directory, initialize a new Git repository there, then push to your new GitHub repo.

Example remote:

`https://github.com/SUPERZJ827/my_harness.git`

## What The Clean Export Should Contain

- code directories: `MetaGPT/`, `experiments/`, `evaluations/`, `role/`, `src/`, `utils/`
- docs: `README.md`, `docs/`
- dependency file: `requirements.txt`
- config template with placeholder API key
- lightweight sample data only: `data/human_0/`
- matching evaluation config: `metric/human_0/`

## What Should Be Excluded

- `venv/`
- `harness/`
- `results_*`
- `evaluation_results/results/`
- `hf_dataset_tmp/`
- large benchmark task folders
- `data/**/gt/` for the full benchmark snapshot
- any real API keys

## After Export

Typical commands inside the clean export directory:

```bash
git init
git branch -M main
git remote add origin https://github.com/SUPERZJ827/my_harness.git
git add .
git commit -m "Initial public snapshot"
git push -u origin main
```
