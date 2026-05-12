# 相对于原始仓库的本地修改说明

本项目基于原始 DataSciBench 仓库和一个本地修改版 MetaGPT fork。

这份文档总结的是这个版本里主要的工程性修改，目的是帮助读者快速理解“这个仓库相对于原始版本做了什么”。它不是逐行 diff，也不是完整的上游对比报告。

## 1. 新增了 TAME 风格执行变体

新增文件：

- `role/tame_config.py`
- `role/tame_artifacts.py`
- `role/tame_recovery.py`
- `role/tame_runtime_state.py`

主要作用：

- 引入可配置的 TAME variants，例如 `full_tame`、`baseline_a_t_plus`、`wo_t_plus` 等
- 把 planning、reflection、retry、recovery、artifact tracking、final guard、step budget 等能力做成可切换配置
- 支持系统化 ablation，而不是每次手工改主流程

## 2. 主运行脚本 `run_examples.py` 被大幅扩展

主要文件：

- `experiments/run_examples.py`

主要改动：

- 增加了 `--tame_variant`
- 支持 `--max_retry`、`--tame_max_steps`、`--task-timeout-seconds`、`--list_tame_variants`
- 运行前会自动把任务输入文件复制到实际 run 目录
- 会根据 `metric/<task_id>/metric.yaml` 自动生成 artifact contract 并注入 prompt
- 增加了对特殊任务输入的处理逻辑，例如 `csv_excel_48`
- 通过 adapter 层支持 DSBench 类型任务
- 输出目录结构更规范，例如：
  - `<output_dir>/<task_id>/<model>__<variant>_<run_index>/`

## 3. 新增了 artifact-aware prompting 与 artifact contract

主要文件：

- `role/tame_artifacts.py`

主要作用：

- 解析评测配置，提取评测真正关心的输出文件名和列名
- 把这些要求转成 prompt contract 注入生成流程
- 减少因为文件名不对、文件缺失、列名不对导致的失败

## 4. 本地 `SciDataInterpreter` 流程被定制化

主要文件：

- `role/sci_data_interpreter.py`

相关 MetaGPT 修改：

- `MetaGPT/metagpt/actions/di/write_analysis_code.py`
- `MetaGPT/metagpt/actions/di/write_plan.py`
- `MetaGPT/metagpt/prompts/di/write_analysis_code.py`
- `MetaGPT/metagpt/provider/openai_api.py`
- `MetaGPT/metagpt/roles/di/data_interpreter.py`
- `MetaGPT/metagpt/strategy/planner.py`

总体效果：

- 上游 Data Interpreter 的行为被调整为更适配当前仓库的 TAME 工作流
- planning、execution、retry、logging 等逻辑更贴近 benchmark 批量实验场景
- MetaGPT 的 prompt 和执行栈被改造得更适应当前任务格式

## 5. 在原始 DataSciBench 运行器之上增加了 DSBench 支持

主要文件：

- `experiments/dsbench_adapter.py`
- `experiments/prepare_dsbench_pilot.py`
- `experiments/run_dsbench_pilot.py`
- `experiments/evaluate_dsbench_pilot.py`
- `experiments/evaluate_dsbench_batch.py`
- `experiments/export_dsbench_official_eval.py`
- `docs/dsbench_official_eval_adapter.md`

新增能力：

- 支持 `dsbench_da_*` 风格任务
- 自动生成 workbook summary、CSV profile 等辅助文件
- 对 `final_answer.txt` 做 DSBench 风格的标准化
- 支持导出成 DSBench 官方评测布局
- 支持在隔离工作区中跑 DSBench 官方 judge

## 6. 增加了 DABStep 支持和 pilot 准备工具

主要文件：

- `experiments/prepare_dabstep_pilot.py`
- `experiments/run_dabstep_pilot.py`
- `experiments/evaluate_dabstep_pilot.py`
- `experiments/dabstep_task_sets.json`
- `docs/dabstep_minimal_pilot.md`

作用：

- 支持准备、运行、评测 DABStep 风格 pilot 任务集
- 让这个仓库不仅能跑原始 DataSciBench，也能做跨 benchmark 的 pilot 实验

## 7. 增加了额外的实验管理和 ablation 工具

主要文件：

- `experiments/prepare_dsbench_ablation_set.py`
- `experiments/evaluate_data_analysis_metrics.py`
- `experiments/summarize_data_analysis_ablation.py`
- `experiments/evaluate_bcb_from_runs.py`
- `experiments/dsbench_task_sets.json`
- `experiments/tame_task_sets.json`

作用：

- 构建任务子集
- 进行 data-analysis 导向的 ablation 评测
- 生成汇总表
- 支持跨多个结果目录做 batch evaluation

## 8. 评测逻辑被增强并做了更多参数化

主要文件：

- `experiments/evaluate.py`
- `evaluations/check_result.py`
- `evaluation_results/calculate_final_metric.py`

主要改动：

- `task_id` 支持单个 id、逗号分隔、Python list 字符串、`all`、`original_55`、`original_full`
- 支持通过 `--skip_vlm` 跳过 VLM 相关评测项
- 支持自定义 `--runs_dir`
- 进度检查逻辑更新为适配新的结果目录结构

## 9. 配置加载和日志逻辑更稳健

主要文件：

- `src/logs.py`

主要改动：

- 配置文件会从多个候选位置自动查找
- logger 创建逻辑适配了新的结构化结果目录
- 结果日志和时间日志做了更清晰的分离

## 10. 多处 prompt 和 metric 文件被修订

影响范围：

- 多个 `data/*/prompt.json`
- 多个 `metric/*/metric.yaml`

目的：

- 让 prompt、输出要求、评测逻辑更一致
- 配合新的执行流程、ablation 设计、DSBench 集成和 artifact contract

## 11. MetaGPT 中的工具 schema 被调整

影响文件：

- `MetaGPT/tools/schemas/` 下多份文件

目的：

- 让 tool recommendation 和工具元信息更贴合当前本地 benchmark 工作流

## 12. 为公开发布做了清理和补充文档

主要文件：

- `README.md`
- `README_ZH.md`
- `docs/github_upload_guide.md`

主要工作：

- 把这个公开快照整理成可以直接 clone 和做轻量验证的状态
- 只保留示例配置，不提交真实密钥
- README 增加了环境配置、命令参考、数据导入说明、排错说明等内容

## 对外简短描述建议

如果你想在 README 或项目介绍里用一句话概括这个版本，可以写成：

> 一个在原始 DataSciBench 基础上本地扩展的版本，集成了修改版 MetaGPT、TAME 风格执行变体、DSBench/DABStep pilot 支持、artifact-aware prompting，以及额外的评测和 ablation 工具链。

## 说明

这份文档是高层级概览，重点是帮助读者理解主要修改方向和工程意图，而不是完整替代上游 diff。
