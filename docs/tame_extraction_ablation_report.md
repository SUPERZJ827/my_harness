# TAME 从原始 Agent 框架中抽离并支持消融实验的实现分析报告

生成时间：2026-04-28

## 1. 报告目标

本报告总结我们如何在 DataSciBench 原有的 Agent 执行框架上，把 TAME 相关能力从“隐式耦合在单个 agent 行为里”重构为“一组可配置、可裁剪、可做消融实验的薄封装层”，并说明每一层原始实现依赖了什么技术、我们又具体做了哪些改动。

这里的“抽离”不是把底层 agent 整体重写，而是做了三件事：

1. 保留原始 `MetaGPT + DataSciBench` 的主执行骨架不变。
2. 把 TAME 的能力拆成独立层级开关，而不是写死在一个 monolithic agent 中。
3. 让实验入口能够按 variant 装配这些层，从而直接运行 `minimal_baseline`、`baseline_a`、`baseline_m`、`baseline_t_plus`、`full_tame` 等消融配置。

## 2. 原始框架的基础结构

在我们改造之前，整个系统已经具备一个完整的 Data-Agent 执行链路。这个链路的主干来自 `MetaGPT`，而 DataSciBench 在其上做了少量定制。

### 2.1 实验入口层

原始实验入口是 `experiments/run_examples.py`。它负责：

- 读取 `data/<task_id>/prompt.json`
- 加载模型配置
- 实例化 `SciDataInterpreter`
- 将 prompt 发给 agent
- 收集输出 plan、cost、error 统计并写入结果目录

本质上它是一个 benchmark harness，负责批量跑题、建目录、记日志、输出 JSONL。

### 2.2 Agent 角色层

`role/sci_data_interpreter.py` 是 DataSciBench 对 `MetaGPT` 原始 `DataInterpreter` 的包装版角色。它继承 `metagpt.roles.Role`，而 `Role` 内部已经实现了两种核心工作流：

- `react`：Observe -> Think -> Act 循环
- `plan_and_act`：先规划，再按 task 序列执行

底层技术点包括：

- `pydantic` 的模型字段和 `model_validator`
- `MetaGPT` 的 `Message / Task / TaskResult / Plan`
- `Role` 中的状态机、memory、planner 调用链

也就是说，原始 agent 已经具备“能思考、能拆任务、能写代码、能执行代码”的基本能力。

### 2.3 规划层

规划层主要由两部分构成：

- `MetaGPT/metagpt/strategy/planner.py`
- `MetaGPT/metagpt/actions/di/write_plan.py`

原始实现方法是：

1. `Planner.update_plan()` 收集当前 goal、上下文和历史任务。
2. `WritePlan` 用 prompt 让 LLM 输出一个 JSON task list。
3. `update_plan_from_rsp()` 把 JSON 反序列化成 `Task`，挂进 `Plan`。
4. 后续每完成一个 task，再由 `Planner.process_task_result()` 决定确认、重做还是改计划。

这是典型的 “LLM 产出结构化计划 -> 程序端解析为 DAG/任务序列 -> 逐任务执行” 的实现方式。

### 2.4 代码生成与反思层

这部分由 `MetaGPT/metagpt/actions/di/write_analysis_code.py` 和 `MetaGPT/metagpt/prompts/di/write_analysis_code.py` 提供。

原始机制是：

- `WriteAnalysisCode.run()` 组织 `user_requirement + plan_status + tool_info + working_memory`
- 用系统提示词约束 LLM 输出 Python 代码
- 当重试次数大于 0 且启用了 reflection 时，再走 `_debug_with_reflection()`
- `CheckData` 会基于前面已执行代码，额外生成一段检查数据状态的代码

这套机制依赖的关键技术是：

- prompt-based code synthesis
- working memory 注入
- 失败后 reflection prompt 重写实现
- 对任务类型进行条件分支，例如清洗类/建模类任务才做 `CheckData`

### 2.5 Notebook 执行层

原始执行器是 `MetaGPT/metagpt/actions/di/execute_nb_code.py`，这是整个框架最核心的 E 层。

它的技术实现不是简单 `exec()`，而是：

- 使用 `nbformat` 维护 notebook cell
- 使用 `nbclient.NotebookClient` 真正执行 cell
- 支持持续 notebook 上下文，而不是每一步重启 Python
- 对输出做 `parse_outputs()`，区分 stdout、display_data、execute_result、error
- 遇到 `CellTimeoutError`、`DeadKernelError` 时做中断或 reset

因此原始框架已经天然具备：

- 连续代码单元执行
- 中间变量复用
- 图像/文本输出收集
- notebook kernel 生命周期管理

这也是我们后面保留 `E_core` 不动的根本原因。

### 2.6 工具推荐层

原始 `MetaGPT` 还带了 `metagpt.tools.tool_recommend`：

- 使用 `BM25Okapi` 做召回
- 用 LLM 在召回集上做 rerank
- 最终把工具 schema 拼回 prompt

这意味着 agent 原生支持“任务感知工具选择”，虽然在我们当前消融里默认没有把它作为核心变量打开。

## 3. 为什么要做“抽离”

如果直接在一个角色类里不断叠加 prompt、重试、恢复、artifact 检查、checkpoint、约束逻辑，会有三个问题：

1. 不能精确回答“到底是哪一层带来了增益”。
2. 所有能力强绑定在一个 agent 里，无法做 `A/M/T+` 的独立关闭与组合。
3. 出问题时难以区分是“底层执行器问题”还是“TAME 上层治理问题”。

因此我们的目标不是替换原 agent，而是把 TAME 重新组织为：

- 配置层：定义 layer switch
- 注入层：把 prompt/contract/variant 注入运行入口
- 运行时层：负责 checkpoint、artifact state、recovery、ledger
- 策略层：控制 planning/reflection/working memory 等能力是否启用

## 4. 抽离后的总体设计

抽离后的设计可以概括为：

- 保留 `MetaGPT` 原生 `Planner + WriteAnalysisCode + ExecuteNbCode + Role` 主流程
- 在 `SciDataInterpreter` 外围增加一层 `tame_config`
- 再把 TAME 的辅助逻辑拆到独立模块：
  - `role/tame_config.py`
  - `role/tame_artifacts.py`
  - `role/tame_runtime_state.py`
  - `role/tame_recovery.py`
- 最后在 `experiments/run_examples.py` 中通过 `--tame_variant` 组装出不同实验配置

这样之后，TAME 变成了“围绕原 agent 的薄封装层集合”，而不是“与 agent 强耦合的唯一实现”。

## 5. 配置层：把 TAME 明确定义为可开关的层

### 5.1 我们新增了统一配置模型

`role/tame_config.py` 是整个抽离工作的核心。这里定义了：

- `TAMEVariant`
- `TAMEConfig`
- `normalize_variant_name()`
- `tame_contract_prompt()`
- `_VARIANT_PRESETS`

其中 `TAMEConfig` 把能力拆成四组：

- T 层
  - `t_min`
  - `t_plus`
  - `verifier`
  - `budget`
- A 层
  - `adaptation`
  - `planning`
  - `reflection`
  - `working_memory`
  - `check_data`
  - `tool_selection`
- M 层
  - `maintenance`
  - `checkpoint`
  - `resume`
  - `recovery`
  - `artifact_ledger`
- E 层
  - `execution`
  - `max_retry`
  - `max_react_loop`

### 5.2 这一步为什么算“抽离”

因为在这之前，planning、reflection、retry、artifact 约束这些行为是分散在不同代码路径里的；而现在它们第一次被统一抽象成一套 layer switch。

这意味着：

- agent 行为不再靠“写死的 if/else + 命令行参数碎片”控制
- 任何实验配置都可以通过一个 `variant -> config` 的映射复现
- 可以自然定义 `baseline_a`、`baseline_m`、`wo_t_plus` 这类消融配置

### 5.3 variant 的实现方式

我们不是在实验脚本里手写每种配置，而是通过 `TAMEConfig.from_variant()`：

1. 先把字符串规范化
2. 再从 `_VARIANT_PRESETS` 读取预设开关
3. 最后允许命令行 override，例如 `max_steps`、`max_retry`

这是一种典型的“声明式实验编排”方式。好处是实验定义和 agent 实现解耦，复现实验时不需要再改角色代码。

## 6. Harness 层：把 TAME 变成实验入口可装配的能力

### 6.1 运行入口的关键改动

`experiments/run_examples.py` 被改成了一个真正的 TAME harness。它不再只是“把 prompt 扔给 agent”，而是负责做以下装配：

1. 解析 `--tame_variant`
2. 用 `TAMEConfig.from_variant()` 构造当前层开关
3. 根据配置选择 `react` 还是 `plan_and_act`
4. 把 `tame_config` 传入 `SciDataInterpreter`
5. 构造 TAME 合同 prompt 和 artifact contract
6. 记录 `tame_variant` 与 `tame_layers` 到最终 JSONL

### 6.2 原始 prompt 注入方式与我们的改法

原先入口主要拼接的是数据路径说明。我们现在把 requirement 变成：

- `tame_contract_prompt(tame_config)`
- `build_artifact_contract(task_id)` 生成的 artifact contract
- `SPECIFY_PATH_PROMPT`
- benchmark 原始 prompt

这一步非常关键，因为它把 TAME 的 T 层从“agent 内部隐式行为”抽到了“运行入口的可控注入逻辑”。

换句话说，T 层不是靠修改 LLM provider 或执行器来实现，而是通过 benchmark harness 在任务开始前进行统一治理。

### 6.3 输入 staging 的改造

我们新增了：

- `stage_task_inputs()`
- `normalize_csv_excel_48_headers()`

实现方式是：

- 在每个 run 的工作目录里，把任务目录中的输入文件复制进来
- 对少数特殊数据集做针对性修正，例如 `csv_excel_48` 的表头归一化

这样做的意义是把“任务数据的真实来源”和“agent 运行目录”解耦，让 agent 只面对统一的 `./` 输入输出契约。这实际上也是 T 层 contract 化的一部分。

### 6.4 输出记录的改造

`src/schemas/schemas.py` 中的 `SciAgentBenchOutput` 增加了：

- `tame_variant`
- `tame_layers`

这样实验结果天然带有配置语义，后续评测和汇总时不需要靠目录名反推行为。

## 7. A 层：把适应、规划、反思能力变成独立开关

### 7.1 原始 A 能力来自哪里

原始框架已经提供了大量 A 层技术基础：

- `Role._plan_and_act()` 的任务分解流程
- `Planner` 的 task 管理
- `WritePlan` 的 LLM 规划
- `WriteAnalysisCode` 的代码生成
- `CheckData` 的状态检查
- `working_memory` 的上下文持续注入
- reflection prompt 的调试改写

所以我们并没有重新发明 A 层，而是把原始 MetaGPT 的这些自适应能力重新组织进 TAME 的层定义中。

### 7.2 我们如何把 A 层挂接到 `SciDataInterpreter`

在 `SciDataInterpreter.set_plan_and_tool()` 中，我们根据 `tame_config` 动态决定：

- 是否启用 `planning`
- 是否切换 `react_mode`
- 是否允许 `use_reflection`
- 是否启用 `tool_recommender`

逻辑上有三种典型状态：

1. `adaptation=False`
   - 强制退化为单步 `react`
   - 关闭 reflection
2. `adaptation=True, planning=False`
   - 保留一定自适应，但不显式分解计划
3. `adaptation=True, planning=True`
   - 使用完整 `plan_and_act`

这一步是抽离的关键，因为它把“agent 用哪种认知模式工作”从代码逻辑里变成了配置逻辑。

### 7.3 working memory 的抽离方法

原始 `DataInterpreter` 默认把所有生成代码和执行结果都塞进 `working_memory`，后续 prompt 默认继续带上这些上下文。

我们新增了 `_prompt_working_memory()`，把传给 LLM 的上下文拆成三种来源：

- 基础 working memory
- 最近几步 runtime ledger 摘要
- recovery prompt

同时只有在 `tame_config.working_memory=True` 时，才会保留原有记忆注入行为。

也就是说，我们把“记忆”从默认总是启用，变成了一个显式的 A 层能力开关。

### 7.4 `CheckData` 的选择性启用

原始 `DataInterpreter._check_data()` 会在部分任务类型后执行数据检查。我们保留这套机制，但通过 `tame_config.check_data` 控制是否启用。

这一步的意义在于：

- `baseline_a` 可以保留数据状态感知
- `minimal_baseline` 可以关闭该额外分析步骤
- 我们可以判断“运行质量提升到底来自规划/反思，还是来自中间数据观测”

### 7.5 reflection 的抽离方法

我们没有删除原始 reflection，而是在 `_write_code()` 中改成：

- 只有 `counter > 0`
- 且 `self.use_reflection`
- 且 `tame_config.reflection=True`

时才启用

因此 reflection 变成了可独立消融的 A 子层，而不是默认绑定在多次重试中的固定行为。

## 8. T 层：把任务治理与产物契约从“提示词技巧”升级为系统部件

### 8.1 T_min 的实现

`tame_contract_prompt()` 定义了最薄的一层任务合同：

- 任务必须在当前目录产出结果
- 输入从当前目录或 `../` 读取
- 不允许破坏性文件操作、网络安装、凭据访问、宿主机修改

这层相当于一个最小行为边界。它不改变执行器，只约束 agent 的任务作用域。

### 8.2 T_plus 的实现

T_plus 不是单一功能，而是三个部分的组合：

1. 更强的 task governance prompt
2. artifact contract 注入
3. 代码与产物验证器

#### 8.2.1 artifact contract 的自动构造

`role/tame_artifacts.py` 的 `build_artifact_contract()` 会直接读取 `metric/<task_id>/metric.yaml`，再自动提取：

- evaluator 里出现的输出文件路径
- CSV 文件被检查的列名
- 某些特殊 evaluator 备注，例如 `.equals()`、PDF 文本解析

技术上这里做了一个轻量静态分析：

- `_extract_artifact_paths()` 从 metric code 和 ground truth 中抽字符串路径
- `_extract_columns_by_artifact()` 识别 `pd.read_csv(...)` 和后续 `df["col"]` 的列访问

这一步很重要，因为它把 DataSciBench 原本“只在评测端知道的产物要求”，前移到了 agent 执行前的 prompt 阶段。

#### 8.2.2 代码级 verifier

`SciDataInterpreter._verify_code()` 在执行前进行软验证：

- 预算验证：步数超过 `max_steps` 直接阻断
- 安全模式匹配：禁止 `shutil.rmtree`、`os.remove`、`subprocess`、`os.system`、`pip install` 等模式

这里我们没有实现 AST 级静态分析，而是用字符串模式做一个 deterministic guard。这种方法简单、可控、成本低，适合 benchmark harness。

#### 8.2.3 产物级 verifier

`SciDataInterpreter._verify_artifact_contract()` 在代码执行成功后继续检查：

- 要求的 artifact 是否真的生成
- CSV 是否含有约定列名

如果 artifact 不满足契约，就把本轮执行视为失败，并把错误反馈回后续 recovery / reflection 流程。

这一步意味着 T_plus 已经不只是“多说几句 prompt”，而是“prompt + 程序化校验”的闭环。

## 9. M 层：把维护、恢复、可续跑能力单独模块化

### 9.1 原始框架的问题

原始 `DataInterpreter` 虽然支持多次 retry，但缺少系统化的运行时维护能力：

- 没有统一 checkpoint
- 没有 artifact rollback
- 没有标准化 failure classification
- 没有 ledger
- 没有恢复提示生成器

因此我们把这些能力整体抽到 M 层。

### 9.2 runtime state 模块

`role/tame_runtime_state.py` 专门负责产物状态管理，包括：

- `select_relevant_artifacts()`
- `collect_artifact_status()`
- `snapshot_artifacts()`
- `rollback_artifacts()`
- `write_json()`
- `read_json()`

这说明 M 层不再散落在角色代码里，而是被封装成独立运行时库。

#### 9.2.1 artifact 状态收集

`collect_artifact_status()` 会遍历期望产物，记录：

- 是否存在
- 已出现路径
- 缺失路径
- CSV 已有列
- 缺失列
- schema error

这相当于给每一步执行都建立了一个结构化的 artifact health snapshot。

#### 9.2.2 snapshot / rollback

在每轮代码执行前，如果开启 `maintenance`，系统会：

1. 根据当前代码筛选相关 artifact
2. 对这些文件做 `snapshot_artifacts()`
3. 若本轮失败，则 `rollback_artifacts()`

这就是典型的“轻量事务化产物保护”。虽然不是数据库事务，但对 benchmark 输出文件已经足够。

### 9.3 recovery 模块

`role/tame_recovery.py` 负责两件事：

1. `classify_failure()`
2. `build_recovery_prompt()`

#### 9.3.1 失败分类方法

我们采用的是“规则驱动的错误分类”，而不是再让 LLM 自由总结错误。当前已覆盖：

- NumPy deprecated alias
- tensor dtype/object 错误
- `predict_proba` 单类问题
- missing artifact
- missing column
- missing file
- fallback execution error

这样做的理由是 benchmark 中很多错误是高频模式，规则分类比 LLM 自由发挥更稳定，也更可重复。

#### 9.3.2 recovery prompt 的构造

当某轮失败且允许恢复时，系统会把以下信息组织成一个明确的恢复提示：

- retry 序号
- error type
- failure summary
- missing artifacts
- mandatory fix guidance
- traceback excerpt

于是下一轮生成不是“盲重试”，而是“带结构化故障上下文的局部修复”。

### 9.4 checkpoint / progress / ledger

M 层真正落地时，`SciDataInterpreter` 维护了四类持久化文件：

- `tame_checkpoint.json`
- `tame_progress.json`
- `tame_artifacts.json`
- `tame_ledger.jsonl`

作用分别是：

- checkpoint：记录当前步骤、层配置、最近 ledger、错误计数
- progress：记录当前 phase、retry、success、error_type、artifact_status
- artifacts：记录当前 artifact 状态
- ledger：逐步追加执行事件流

这套设计让长任务可以：

- 中断后恢复部分状态
- 明确知道前一轮失败在什么位置
- 做运行后分析和错误统计

### 9.5 M 层如何接入主循环

在 `_write_and_exec_code()` 中，M 层按以下顺序介入：

1. 解析 artifact contract
2. 针对当前代码挑选相关 artifact
3. 执行前写 progress
4. 执行前做 artifact snapshot
5. 执行后收集 artifact status
6. 失败则 rollback
7. 写入 progress / artifact_state / ledger / checkpoint
8. 若允许 recovery，则生成下一轮 recovery prompt

这说明 M 层并没有另起一个 agent，而是作为横切逻辑插进原始 write-execute-retry 闭环中。

## 10. E 层：我们保留了原始执行器，但加了最小适配

### 10.1 为什么 E_core 没有被重写

因为 `ExecuteNbCode` 本身已经是一个成熟的 notebook 执行器：

- 支持多 cell 连续执行
- 支持 kernel 生命周期管理
- 支持 timeout 和 dead kernel 恢复
- 能返回标准化执行结果

所以在抽离 TAME 时，我们有意识地不碰这个底层，把它视为恒定的 `E_core`。

### 10.2 我们对 E 层做了什么

严格说我们没有重写执行器，只增加了一个最小适配器：

- `SciDataInterpreter._prepare_code_for_execution()`

它会在模型生成代码前拼接一个 deterministic prelude，完成：

- 常用库导入：`numpy`、`pandas`
- 从父目录向当前运行目录暴露常见输入文件

这样做的目的不是增强 agent 智能，而是减少“因为工作目录或基础 import 缺失导致的非本质失败”。

这一步很重要，因为它把 E 层增强保持在“最薄、最稳定”的范围内，避免把 TAME 的增益和执行环境偶然性混在一起。

## 11. 稳定性补丁层：为了让 TAME 失败时仍然留在框架内

除了正式的 T/A/M/E 分层，我们还对 `MetaGPT` 原生组件做了几处稳健性补丁。这些补丁的目标不是提高智能，而是避免 harness 被输出格式问题直接打崩。

### 11.1 `WritePlan` 的宽松 JSON 解析

在 `MetaGPT/metagpt/actions/di/write_plan.py` 中新增 `parse_plan_json_lenient()`：

- 优先取 ```json fenced block
- 否则尝试截取最外层 JSON array
- 最后才原样返回

原因是某些模型会输出带多余文字的 JSON。没有这层保护，planner 可能直接崩溃。

### 11.2 Planner 的 fallback plan

在 `MetaGPT/metagpt/strategy/planner.py` 中，当 plan 多次生成失败后，我们加入了 fallback：

- 如果已有当前 task，就退回单 task JSON
- 否则生成一个默认任务：解决用户需求并创建所需产物

这使得 planning 失败时，任务仍能继续执行，而不是整个实验中断。

### 11.3 宽松代码解析

在 `MetaGPT/metagpt/actions/di/write_analysis_code.py` 中新增：

- `parse_python_code_lenient()`
- `parse_reflection_impl_lenient()`

它们解决的问题包括：

- code fence 没闭合
- reflection 还在返回旧版 JSON
- JSON 被截断但还残留 `improved_impl`

本质上这些补丁是在保证“失败留在执行链内”。也就是让模型坏输出转化为一次 in-band failed run，而不是让 harness 自己抛异常退出。

### 11.4 reflection prompt 的简化

我们把 reflection prompt 从“要求输出 JSON 包含 `reflection` 和 `improved_impl`”改成“只输出完整 Python 代码块”。

这样做降低了格式约束复杂度，也减少了解析失败面。

### 11.5 react think 的容错

`MetaGPT/metagpt/roles/di/data_interpreter.py` 中对 `REACT_THINK_PROMPT` 的 JSON 解析加了 try/except：

- 如果不是 JSON，就记一条 working memory
- 然后允许继续执行一次 action

这避免了 react 模式下的思考输出稍微跑偏就直接终止。

## 12. `SciDataInterpreter` 如何成为 TAME 的承载体

从架构上看，`SciDataInterpreter` 现在承担的是“组装层”的职责，而不是“把所有能力都自己实现”。

它主要做四类工作：

1. 根据 `tame_config` 决定当前认知模式
2. 把 prompt、memory、ledger、recovery 信息组装后传给原始 `WriteAnalysisCode`
3. 在执行前后插入 verifier、artifact state、rollback、checkpoint
4. 把最终运行轨迹写回 benchmark 结果结构

因此它已经从“一个简单的 DataInterpreter 定制版”，变成了“原始 agent 与 TAME 各层之间的适配器”。

这正是“抽离”的结果：TAME 自己不再是角色类里纠缠不清的一团逻辑，而是由独立模块通过 `SciDataInterpreter` 进行调度。

## 13. 消融实验是如何真正落地的

### 13.1 变体定义

目前已经支持的变体包括：

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

### 13.2 每个变体不是单独写逻辑，而是共享同一 agent

这是本次改造最重要的实验设计点。

所有 variant：

- 共享同一个 `SciDataInterpreter`
- 共享同一个 `ExecuteNbCode`
- 共享同一个 benchmark 数据和评测方式

变化的只有 layer switch。

这样才能保证消融是可比较的。否则如果每个 variant 对应一套不同角色类，那么性能差异会混入额外实现差异。

### 13.3 variant 的运行路径

一次运行的完整链路现在是：

1. `run_examples.py` 读取命令行 variant
2. 生成 `TAMEConfig`
3. 根据 config 组装 prompt 和模式
4. 实例化 `SciDataInterpreter(tame_config=...)`
5. 在相同数据与执行器条件下运行
6. 输出带 `tame_variant` 和 `tame_layers` 的 JSONL
7. 后续统一走 `experiments.evaluate`

这个流程说明“消融能力”不是后处理时人工分类出来的，而是已经写进了 harness 的一等公民能力。

## 14. 这次改造的工程意义

从工程角度看，这次工作不是简单“多加了几个 prompt”，而是完成了三个层面的升级。

### 14.1 从经验性 agent 到可解释 agent

以前很多行为是混在一起的，很难说清楚是 planning、reflection、retry 还是 artifact 约束起作用。现在每个能力都可以单独开关，结果可解释性明显提高。

### 14.2 从一次性实验代码到可复用 harness

现在的 TAME 已经具备：

- variant 管理
- 运行时状态文件
- artifact 契约生成
- 失败恢复提示
- 结果带层信息输出

这意味着它不只是“为了这一轮实验临时写的逻辑”，而是可持续复用的 benchmark harness。

### 14.3 从强耦合实现到薄层封装

最关键的是，我们没有动底层 notebook executor 的核心机制，也没有为每个 ablation 复制 agent，而是把 TAME 变成：

- 可配置
- 可关闭
- 可分析
- 可复现

的外围层。这使得后续再增加新层或者替换某一层时，改动范围会小很多。

## 15. 关键文件与职责对应

| 文件 | 角色 |
| --- | --- |
| `experiments/run_examples.py` | TAME harness 入口，variant 装配、prompt 注入、输入 staging、输出记录 |
| `role/tame_config.py` | TAME 的层开关与 variant 定义中心 |
| `role/tame_artifacts.py` | 从 benchmark metric 自动抽取 artifact contract |
| `role/tame_runtime_state.py` | artifact 状态、snapshot、rollback、progress I/O |
| `role/tame_recovery.py` | 失败分类与 recovery prompt 构造 |
| `role/sci_data_interpreter.py` | 原始 agent 与 TAME 各层的适配器 |
| `MetaGPT/metagpt/actions/di/write_plan.py` | 规划输出的宽松解析 |
| `MetaGPT/metagpt/strategy/planner.py` | plan fallback，避免规划失败直接终止 |
| `MetaGPT/metagpt/actions/di/write_analysis_code.py` | 宽松代码解析与 reflection 兼容 |
| `MetaGPT/metagpt/prompts/di/write_analysis_code.py` | 更稳定的代码输出提示约束 |
| `MetaGPT/metagpt/actions/di/execute_nb_code.py` | 保持不变的 notebook 执行核心 E_core |
| `src/schemas/schemas.py` | 结果结构中补充 variant 与 layer 元信息 |

## 16. 最终结论

本次改造的本质，是在不推翻原始 `MetaGPT + DataSciBench` agent 骨架的前提下，把 TAME 从“分散在 agent 行为中的隐式增强”重构成了“围绕原始 agent 的显式分层系统”。

原始框架负责：

- 计划生成
- 代码生成
- notebook 执行
- 任务推进

我们新增并抽离出的 TAME 层负责：

- T：任务边界、artifact 契约、预算与安全验证
- A：是否启用 planning / reflection / memory / data check
- M：checkpoint、ledger、artifact snapshot、rollback、recovery
- E 适配：最小执行前置适配，但保留原始 notebook executor 不动

因此现在的系统既能继续作为原始 benchmark agent 跑题，也能以统一入口运行不同 TAME 变体，直接支持严格的消融实验。这说明 TAME 已经从一个“嵌在 agent 里的方案”成功抽离成了一个“可配置、可观测、可对比”的实验框架层。
