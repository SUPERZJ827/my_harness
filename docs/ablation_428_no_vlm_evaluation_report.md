# 428 批次非 VLM 评估汇总

生成时间：2026-04-28

## 评估设置

- 结果目录：`*_20_428`
- 评估命令：`./harness/bin/python -m experiments.evaluate --task_id all --model_id deepseek-v4-flash --runs_dir <runs_dir> --skip_vlm`
- 说明：本次使用 `--skip_vlm`，因此 VLM-as-a-judge 相关评估项被跳过，且不计入 Completion Rate。
- 单独保存的评估结果文件：
  - `evaluation_results/deepseek-v4-flash__minimal_baseline_20_428_no_vlm_results.csv`
  - `evaluation_results/deepseek-v4-flash__baseline_t_plus_20_428_no_vlm_results.csv`
  - `evaluation_results/deepseek-v4-flash__baseline_a_20_428_no_vlm_results.csv`
  - `evaluation_results/deepseek-v4-flash__baseline_m_20_428_no_vlm_results.csv`
  - `evaluation_results/deepseek-v4-flash__full_tame_20_428_no_vlm_results.csv`

## 汇总表

| 配置 | 任务数 | Avg CR | Pass@1 | Human Avg CR | DL Avg CR | CSV Avg CR | Human Pass@1 | DL Pass@1 | CSV Pass@1 | F1 | F2 | F3 | F4 | F5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| minimal_baseline | 20 | 40.59% | 10.00% | 51.57% | 24.17% | 37.82% | 22.22% | 0.00% | 0.00% | 75.00% | 0.00% | 43.75% | 66.67% | 10.00% |
| baseline_t_plus | 20 | 48.42% | 10.00% | 59.44% | 15.83% | 59.03% | 11.11% | 0.00% | 16.67% | 62.50% | 0.00% | 37.50% | 100.00% | 35.00% |
| baseline_a | 20 | 54.53% | 10.00% | 63.06% | 44.17% | 50.38% | 22.22% | 0.00% | 0.00% | 70.83% | 0.00% | 56.25% | 100.00% | 10.00% |
| baseline_m | 20 | 48.59% | 15.00% | 60.56% | 44.17% | 34.34% | 22.22% | 20.00% | 0.00% | 66.67% | 0.00% | 50.00% | 100.00% | 5.00% |
| full_tame | 20 | 63.57% | 15.00% | 69.72% | 51.67% | 64.27% | 22.22% | 0.00% | 16.67% | 83.33% | 50.00% | 62.50% | 100.00% | 30.00% |

## 主要观察

### 总体排序

在去掉 VLM 指标后，整体排序没有发生变化：

1. `full_tame` 仍然是综合最优，`Avg CR=63.57%`
2. `baseline_a` 仍是最强单模块，`Avg CR=54.53%`
3. `baseline_m` 与 `baseline_t_plus` 接近，分别为 `48.59%` 和 `48.42%`
4. `minimal_baseline` 最低，`Avg CR=40.59%`

### T_plus 的特征

`baseline_t_plus` 仍然表现出明显的结构化输出优势：

- `CSV Avg CR=59.03%`，高于 `baseline_a=50.38%`
- `F5=35.00%`，明显高于 `baseline_a=10.00%` 和 `baseline_m=5.00%`

但它在 DL 子集仍然偏弱：

- `DL Avg CR=15.83%`
- `DL Pass@1=0.00%`

### A 层的特征

`baseline_a` 的特点仍是更稳：

- `Avg CR=54.53%`
- `Human Avg CR=63.06%`
- `DL Avg CR=44.17%`

说明 A 层对于多步推理、任务分解和流程推进仍是主要增益来源。

### Full TAME 的特征

`full_tame` 依然在几乎所有关键维度上最强：

- `Avg CR=63.57%`
- `Pass@1=15.00%`
- `Human Avg CR=69.72%`
- `DL Avg CR=51.67%`
- `CSV Avg CR=64.27%`
- `F1=83.33%`
- `F2=50.00%`
- `F3=62.50%`
- `F4=100.00%`
- `F5=30.00%`

这说明在去掉 VLM 后，Full 的优势并不是由视觉评估项“抬出来”的，而是来自非 VLM 的清洗、统计、建模、文件对齐等主体能力。

## 结论

去除 VLM 指标后，`428` 这一批结果的主要结论保持稳定：

- `full_tame` 仍然是总体最强配置
- `baseline_a` 仍然是最强单层
- `baseline_t_plus` 的主要收益仍集中在结构化输出与 CSV 类任务
- `baseline_m` 更偏执行稳定性和部分通过率提升

因此，之前基于含 VLM 结果得到的主要结论并没有因为去掉 VLM 而被推翻。
