# DataSciBench 公开仓库说明

本地修改说明： [docs/local_modifications_ZH.md](docs/local_modifications_ZH.md)

这是一个经过清理后的 `DataSciBench + MetaGPT` 本地修改版公开快照。

这个公开版本的目标很明确：

- 让其他用户可以直接 clone 下来并理解如何运行
- 保留核心代码和本地修改过的 `MetaGPT/`
- 去掉本地大体积实验结果和运行环境
- 避免泄露真实 API key

当前这个公开快照只保留了一个轻量示例任务 `data/human_0/`，方便新用户先验证整条流程是否跑通，而不需要一开始就下载完整 benchmark。

## 仓库里包含什么

- `MetaGPT/`：本项目依赖的本地修改版 MetaGPT 源码
- `experiments/`：主运行脚本和数据准备脚本
- `evaluations/`：进度检查脚本和一些 shell 辅助脚本
- `role/`、`src/`、`utils/`：核心逻辑
- `metric/`：评测配置
- `data/human_0/`：轻量 smoke test 示例任务
- `docs/`：面向公开仓库保留的操作说明文档

## 仓库里刻意不包含什么

这个仓库不会打包完整 benchmark 数据、较大的 `gt/` 真值产物、本地虚拟环境，也不会打包你本地的 `results_*` 等实验结果目录。

如果你需要完整 benchmark 数据和原始项目背景，请参考：

- 原始项目：`https://github.com/THUDM/DataSciBench`
- 数据集：`https://huggingface.co/datasets/zd21/DataSciBench/tree/main`

## 推荐运行环境

- 操作系统：推荐 Linux
- Python：推荐 `3.10`
- MetaGPT `setup.py`` 要求的最低 Python 版本：`>=3.9`

## 关键目录说明

新用户最需要关心的是这些路径：

- `experiments/run_examples.py`：主生成入口
- `experiments/evaluate.py`：主评测入口
- `evaluations/check_result.py`：生成进度检查
- `config/config2.example.yaml`：模型配置示例
- `data/human_0/`：仓库自带的轻量示例任务
- `metric/human_0/metric.yaml`：示例任务对应的评测配置

## 完整配置流程

### 1. clone 仓库

```bash
git clone https://github.com/SUPERZJ827/my_harness.git
cd my_harness
```

### 2. 创建 Python 环境

使用 `venv`：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. 安装仓库内自带的本地 MetaGPT

这个项目依赖当前仓库里的 `MetaGPT/` 源码，不建议随意替换成其他环境里的 MetaGPT。

```bash
cd MetaGPT
pip install .
cd ..
```

同时，`MetaGPT/requirements.txt` 也已经按照维护者当前 `harness` 环境的实际版本做了锁定。

### 4. 数据

原始 DataSciBench 的组织方式里，处理后的 prompt 会放在：

```text
data/<task_id>/
```

这个公开快照目前只保留了一个轻量示例任务：

```text
data/human_0/
```

如果你想运行更多任务，请看本文后面的“完整数据导入”部分。

### 5. 安装项目依赖

```bash
pip install -r requirements.txt
```

根目录 `requirements.txt` 现在已经按维护者本地 `/home/zhoujun/DataSciBench/harness` 环境锁定版本，依赖解析会比原先的宽松写法更稳定。

### 6. 创建运行配置文件

先从示例文件复制：

```bash
cp config/config2.example.yaml config/config2.yaml
```

然后编辑 `config/config2.yaml`，填入你自己的模型配置：

```yaml
llm:
  api_type: "openai"
  model: "deepseek-v4-flash"
  base_url: "https://api.deepseek.com/v1"
  api_key: "YOUR_API_KEY"
```

说明：

- `api_key` 需要替换成你自己的真实 key
- 不要把 `config/config2.yaml` 提交到 GitHub
- 仓库里只保留示例配置文件

如果你还想额外保留一份 MetaGPT 侧的本地示例，也可以参考：

- `MetaGPT/config/config2.example.local.yaml`

### 7. `--config` 参数到底会去哪里找配置

当你传入 `--config config2.yaml` 时，代码大致会按以下顺序搜索：

1. `MetaGPT/config/config2.yaml`
2. `MetaGPT/config2.yaml`
3. `config/config2.yaml`
4. MetaGPT home 配置目录
5. 项目根目录
6. 当前工作目录

对于这个公开仓库，推荐你实际使用的文件是：

- `config/config2.yaml`

## 最快跑通 smoke test

这是新用户最低门槛跑通整条链路的方式。

### 运行仓库自带的示例任务

```bash
python -m experiments.run_examples \
  --task_id human_0 \
  --max_runs 1 \
  --config config2.yaml \
  --output_dir results
```

### 评测这个示例任务

`--model_id` 需要和你的配置文件中的 `llm.model` 对应。例如如果配置里写的是 `deepseek-v4-flash`：

```bash
python -m experiments.evaluate \
  --task_id human_0 \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

### 检查生成进度

```bash
python -m evaluations.check_result \
  --model_id deepseek-v4-flash \
  --runs_dir results
```

## 输出目录大致长什么样

每次运行的结果通常会写到：

```text
results/<task_id>/<model_name>__<tame_variant>_<run_index>/
```

例如：

```text
results/human_0/deepseek-v4-flash__full_tame_0/
```

一个典型运行目录里通常会有：

- `logs.txt`
- `sys_logs.txt`
- 该任务生成的输出文件

此外，还可能有聚合后的输出文件，例如：

```text
results/human_0/deepseek-v4-flash__full_tame_outputs.jsonl
```

## 数据准备与 gt 目录规范

这一部分通常才是最容易把人卡住的地方。

在这个项目里，一个可运行任务不只是一个 prompt，而通常需要同时具备三部分：

1. `data/` 下的任务目录
2. `metric/` 下同名的评测目录
3. `data/<task_id>/gt/` 下的真值文件

### 单个任务最小目录规范

假设任务叫 `human_0`，推荐目录结构如下：

```text
data/
  human_0/
    prompt.json
    data.csv                  # 如果任务依赖输入数据，就放这里
    other_input_file.ext      # 其他输入文件，可选
    gt/
      expected_output.ext
      test_gt.py              # 可选，取决于评测方式

metric/
  human_0/
    metric.yaml
```

### 每一类文件分别是干什么的

`data/<task_id>/prompt.json`
: 任务定义文件。这个是必须的。里面至少要有任务 prompt，很多时候还会带 `data_source_type` 字段，供筛选任务时使用。

`data/<task_id>/...`
: 任务输入文件。运行时，脚本会把这些文件拷贝到实际运行目录中。支持的输入文件包括 `.csv`、`.xlsx`、`.xls`、`.json`、`.txt`、`.md`、`.parquet`、图片、`.npy`、`.pkl`、`.h5`、`.pth` 等。

`data/<task_id>/gt/`
: 真值目录。评测时会把这里当作 ground truth 基目录。

`metric/<task_id>/metric.yaml`
: 评测配置文件。它定义了具体要跑哪些 metric，以及这些 metric 要去 `gt/` 目录下找哪些真值文件。

### ground truth 是怎么解析的

评测时，代码会把：

```text
data/<task_id>/gt/
```

当作 ground truth 根目录。

然后 `metric/<task_id>/metric.yaml` 里的每个 metric 都可以写一个相对于这个目录的文件名。

例如，如果 `metric.yaml` 里写的是：

```yaml
ground_truth: most_corr_output.csv
```

那么评测器最终去找的就是：

```text
data/human_0/gt/most_corr_output.csv
```

所以实际规则很简单：

- 真值文件统一放在 `data/<task_id>/gt/`
- `metric.yaml` 里的 `ground_truth` 写相对于 `gt/` 的路径

### 当前仓库内置示例任务的真实对应关系

这个仓库自带的示例任务是：

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

而它对应的 `metric.yaml` 里会写：

```yaml
ground_truth: most_corr_output.csv
```

这就表示评测时会读取：

```text
data/human_0/gt/most_corr_output.csv
```

### 不同类型任务至少需要什么文件

情况 1：纯 prompt 任务，没有额外输入文件

最少需要：

```text
data/<task_id>/prompt.json
data/<task_id>/gt/<expected_output>
metric/<task_id>/metric.yaml
```

情况 2：依赖 CSV / Excel 等输入数据的任务

最少需要：

```text
data/<task_id>/prompt.json
data/<task_id>/input_file.csv
data/<task_id>/gt/<expected_output>
metric/<task_id>/metric.yaml
```

情况 3：使用自定义评测脚本的任务

通常还会带：

```text
data/<task_id>/gt/test_gt.py
metric/<task_id>/metric.yaml
```

### 如果你要手动新增任务，推荐流程

最稳妥的做法是：

1. 新建 `data/<task_id>/`
2. 放入 `prompt.json`
3. 把该任务所需的所有输入文件放进这个目录
4. 新建 `data/<task_id>/gt/`
5. 把评测会用到的标准输出文件放进 `gt/`
6. 新建 `metric/<task_id>/metric.yaml`
7. 确保 `metric.yaml` 中每个 `ground_truth:` 都是相对于 `data/<task_id>/gt/` 的路径

### 如果你要接入完整 benchmark 数据

这个公开仓库默认不自带完整数据集。你自己下载完整 benchmark 之后，目标就是把目录恢复成同样的逻辑结构：

```text
data/<task_id>/...
metric/<task_id>/metric.yaml
data/<task_id>/gt/...
```

实际操作建议：

1. 下载原始 benchmark 任务目录
2. 把每个任务目录复制到 `data/`
3. 确保 `metric/` 下有对应同名目录
4. 确保每个任务都有可用的 `gt/` 目录

### 更偏操作手册的导入流程

如果你希望按步骤执行，可以直接按下面这个流程来。

第 1 步：先下载原始任务数据

- 先把 benchmark 任务目录下载到一个临时目录
- 不建议一下载完就直接混到当前仓库里

第 2 步：先检查下载下来的目录结构

理想情况下，下载内容应该接近：

```text
<download_root>/
  human_0/
  human_1/
  csv_excel_0/
  dl_0/
  ...
```

对于每个任务目录，至少先确认：

- 存在 `prompt.json`
- 如果任务依赖输入数据，目录里有 `.csv` / `.xlsx` / `.json` 等文件
- 如果下载包本身带真值，应该能看到 `gt/`

第 3 步：把任务目录复制到 `data/`

确认结构没问题之后，再把任务目录复制到：

```text
data/<task_id>/
```

第 4 步：确认 `metric/` 里有同名任务目录

对于每个你想运行的任务，都必须确认：

```text
metric/<task_id>/metric.yaml
```

存在。

第 5 步：检查每个任务有没有 `gt/`

对于每个导入任务，都检查：

```text
data/<task_id>/gt/
```

是否存在。

如果没有 `gt/`，生成流程可能还能跑，但评测流程通常无法正确工作，除非你后面自己补齐真值文件。

第 6 步：先抽一个任务做完整检查

不要一上来就直接跑全量。先挑一个任务，确认：

- `data/<task_id>/prompt.json` 存在
- 输入文件都在
- `metric/<task_id>/metric.yaml` 存在
- `data/<task_id>/gt/` 存在

第 7 步：先做单任务 smoke test

例如：

```bash
python -m experiments.run_examples \
  --task_id human_1 \
  --max_runs 1 \
  --config config2.yaml \
  --output_dir results_import_check
```

然后立刻评测：

```bash
python -m experiments.evaluate \
  --task_id human_1 \
  --runs_dir results_import_check \
  --model_id deepseek-v4-flash
```

如果一个新导入任务能够完整跑通，那么剩下的大多数任务通常也能按同样逻辑接进去。

### 数据导入后建议立刻跑的检查命令

统计 `data/` 下有多少任务目录：

```bash
find data -mindepth 1 -maxdepth 1 -type d | wc -l
```

统计 `metric/` 下有多少评测目录：

```bash
find metric -mindepth 1 -maxdepth 1 -type d | wc -l
```

检查哪些 `data/` 任务没有对应的 `metric/`：

```bash
for d in data/*; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  [ -f "metric/$name/metric.yaml" ] || echo "missing metric: $name"
done
```

检查哪些任务缺少 `gt/`：

```bash
for d in data/*; do
  [ -d "$d" ] || continue
  [ -d "$d/gt" ] || echo "missing gt: $(basename "$d")"
done
```

检查哪些任务缺少 `prompt.json`：

```bash
for d in data/*; do
  [ -d "$d" ] || continue
  [ -f "$d/prompt.json" ] || echo "missing prompt: $(basename "$d")"
done
```

### 如果你下载到的数据本身不带 `gt/`

这时你需要自己补出评测结构：

1. 新建 `data/<task_id>/gt/`
2. 把评测要用的标准输出文件放进去
3. 修改 `metric/<task_id>/metric.yaml`，让每个 `ground_truth:` 指向相对于 `gt/` 的正确路径

例如：

```text
data/human_8/gt/final_report.csv
metric/human_8/metric.yaml
```

那么 `metric.yaml` 里可以写：

```yaml
ground_truth: final_report.csv
```

### 如果你下载到的是嵌套的 `gt/gt/`

有些本地快照里可能会同时出现：

```text
data/<task_id>/gt/
data/<task_id>/gt/gt/
```

但这个项目的评测器默认把：

```text
data/<task_id>/gt/
```

当作 ground-truth 根目录。

所以更稳妥的做法是：

- 真值文件直接放在 `data/<task_id>/gt/` 下
- 除非你自己明确改过 `metric.yaml`，否则不要依赖 `gt/gt/`

### 数据准备里最常见的错误

错误 1：

- 把真值文件放在了 `data/<task_id>/` 根目录，而不是 `data/<task_id>/gt/`

错误 2：

- 在 `metric.yaml` 里写了绝对路径，而不是相对于 `gt/` 的路径

错误 3：

- 只复制了 prompt，没有复制对应的输入数据文件

错误 4：

- 有 `data/<task_id>/`，但是没有 `metric/<task_id>/metric.yaml`

错误 5：

- `data/` 和 `metric/` 里的任务目录名不完全一致

## 主命令说明

### 1. 生成：`python -m experiments.run_examples`

这是最核心的主运行脚本。

基本写法：

```bash
python -m experiments.run_examples --config config2.yaml
```

常见示例：

只跑一个示例任务：

```bash
python -m experiments.run_examples \
  --task_id human_0 \
  --max_runs 1 \
  --config config2.yaml \
  --output_dir results
```

运行所有 `human_*` 任务：

```bash
python -m experiments.run_examples \
  --data_type human \
  --config config2.yaml \
  --output_dir results
```

运行预定义的 55 任务集合：

```bash
python -m experiments.run_examples \
  --task_id original_55 \
  --max_runs 1 \
  --config config2.yaml \
  --output_dir results
```

切换 TAME variant：

```bash
python -m experiments.run_examples \
  --task_id human_0 \
  --max_runs 1 \
  --tame_variant baseline_a_t_plus \
  --config config2.yaml \
  --output_dir results
```

为单个任务增加超时限制：

```bash
python -m experiments.run_examples \
  --task_id human_0 \
  --max_runs 1 \
  --task-timeout-seconds 900 \
  --config config2.yaml \
  --output_dir results
```

查看支持的 TAME variant：

```bash
python -m experiments.run_examples --list_tame_variants
```

接近真实实验、参数较多的完整示例：

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

这个命令的含义：

- 跑预定义的 `original_55` 任务集合
- 每个任务重复 3 次
- 结果写到 `results_55tasks/`
- 使用 `full_tame` 预设
- 开启 reflection 和 hard retry
- 覆盖默认 retry 次数和 T+ steps
- 单个任务超过 1800 秒就中止

如果你想切到 react 风格，可以额外加：

```bash
--use_react
```

#### `experiments.run_examples` 主要参数说明

`--task_id`
: 要运行的任务 id，例如 `human_0`、`dl_0`、`original_55`。如果不传，脚本会扫描 `data/` 目录。

`--data_source_type`
: 按 `prompt.json["data_source_type"]` 过滤任务。只有在你想做细粒度筛选时才需要。

`--max_runs`
: 每个任务重复运行次数。默认是 `3`。

`--gt_prompt`
: 在原任务 prompt 之前额外拼接一段自定义 prompt。

`--continue_gen`
: 继续之前的运行，而不是因为已有日志而跳过。

`--output_dir`
: 结果根目录。默认是 `results`。

`--data_type`
: 按任务大类过滤。默认是 `human`。常见值：`human`、`dl`、`bcb`、`csv`、`all`。

`--skip_bcb`
: 即使 `data/` 里有 BCB 任务，也跳过它们。

`--use_reflection`
: 启用 TAME 配置里的 reflection 相关行为。

`--hard_retry`
: 启用更强的重试逻辑。

`--max_retry`
: 覆盖 TAME 默认重试次数。

`--use_react`
: 从 plan-and-act 切换为 react 风格执行。

`--tame_variant`
: TAME 预设名。默认是 `full_tame`。

`--tame_max_steps`
: 覆盖 T+ 的执行步数预算。

`--task-timeout-seconds`
: 给单个任务加 wall-clock 超时。

`--list_tame_variants`
: 打印所有支持的 TAME variant 后退出。

`--config`
: 配置文件路径或名称。代码里的默认值是 `test_config.yaml`，但在这个公开仓库里你一般应该显式传 `--config config2.yaml`。

### 2. 评测：`python -m experiments.evaluate`

这个脚本会读取生成好的结果目录，并用 `metric/<task_id>/metric.yaml` 做评测。

基本写法：

```bash
python -m experiments.evaluate \
  --task_id human_0 \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

常见示例：

评测单个任务：

```bash
python -m experiments.evaluate \
  --task_id human_0 \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

评测多个任务：

```bash
python -m experiments.evaluate \
  --task_id human_0,human_1,human_2 \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

评测 `data/` 下当前存在的全部任务：

```bash
python -m experiments.evaluate \
  --task_id all \
  --runs_dir results \
  --model_id deepseek-v4-flash
```

跳过 VLM 相关评测：

```bash
python -m experiments.evaluate \
  --task_id human_0 \
  --runs_dir results \
  --model_id deepseek-v4-flash \
  --skip_vlm
```

和上面“高参数实验命令”对应的评测命令：

```bash
python -m experiments.evaluate \
  --task_id original_55 \
  --runs_dir results_55tasks \
  --model_id deepseek-v4-flash \
  --skip_vlm
```

#### `experiments.evaluate` 主要参数说明

`--requirement`
: 内部/调试字段，通常不用传。

`--plan`
: 内部/调试字段，通常不用传。

`--metric_path`
: 显式指定 metric 文件路径。通常不需要，因为脚本默认会去找 `metric/<task_id>/metric.yaml`。

`--debug_mode`
: 把一些 debug 或特殊 run 也纳入扫描。

`--task_id`
: 任务选择器，支持：
- 单个 id，例如 `human_0`
- 逗号分隔，例如 `human_0,human_1`
- Python list 字符串，例如 `"[\"human_0\", \"human_1\"]"`
- `all`
- `original_55`
- `original_full`

`--model_id`
: 用来匹配结果目录前缀的模型名。通常应该和你配置文件里的 `llm.model` 保持一致。

`--runs_dir`
: 需要评测的结果根目录。默认是 `results`。

`--skip_vlm`
: 跳过依赖 VLM/API 的评测项。

`--include_bcb`
: 评测时包含 BCB 任务。

评测输出通常会写到：

```text
evaluation_results/<model_name>_results.csv
```

### 3. 进度检查：`python -m evaluations.check_result`

这个脚本用于快速检查有多少任务完成、多少任务生成了有效日志。

示例：

```bash
python -m evaluations.check_result \
  --model_id deepseek-v4-flash \
  --runs_dir results
```

参数说明：

`--model_id`
: 需要检查的模型 id，也可以传 `all`。

`--runs_dir`
: 要检查的结果根目录。默认是 `results`。

## 当前支持的 TAME variants

当前支持这些名字：

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

默认值是：

- `full_tame`

如果你不确定该选什么，就先用 `full_tame`。

## 以后如果要接入完整 benchmark 数据

这个公开仓库默认只保留 `data/human_0/`，目的是降低第一次使用门槛。

如果你想跑更多任务：

1. 从原始数据源下载完整 benchmark 数据
2. 把任务目录放到 `data/` 下
3. 确保 `metric/` 下有对应任务的评测配置
4. 再用更大的 `--task_id` 或更宽的 `--data_type` 去运行

## 常见问题

### 1. 找不到 `config2.yaml`

原因：

- 你只复制了 example 文件，但还没有生成实际运行配置文件

解决：

```bash
cp config/config2.example.yaml config/config2.yaml
```

### 2. 生成跑完了，但评测找不到对应 run

原因：

- `--model_id` 和 `config/config2.yaml` 里的模型名不一致

解决：

- 保证生成和评测使用的是同一个模型字符串
- 比如配置里写的是 `deepseek-v4-flash`，那评测就用 `--model_id deepseek-v4-flash`

### 3. 某些任务被莫名跳过

常见原因：

- `--data_type` 把它过滤掉了
- 之前已有日志，而你没有加 `--continue_gen`
- 任务目录里的 `prompt.json` 无法正常读取

### 4. 为什么没有完整 benchmark 任务

这是这个公开快照的刻意设计。仓库默认只带一个轻量示例任务。

## 最短上手流程总结

如果你只想给别人一份最短可复制流程，可以直接用这一段：

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

编辑 `config/config2.yaml` 后，执行：

```bash
python -m experiments.run_examples --task_id human_0 --max_runs 1 --config config2.yaml --output_dir results
python -m experiments.evaluate --task_id human_0 --runs_dir results --model_id deepseek-v4-flash
python -m evaluations.check_result --model_id deepseek-v4-flash --runs_dir results
```
