# Tested Agent 知识地图重建实验

[English](experimental_design.md)

> 状态：面向预注册的实验设计；尚未产生任何比较运行结果。

## 1. 研究目标与主张边界

本实验考察：在固定轮次预算下，Tested Agent 能否通过主动选择诊断问题，更准确、更高效地重建用户的节点级 Knowledge Map。

Reviewed Knowledge Graph 对 Agent 公开。隐藏对象是用户在图谱节点上的掌握状态。本实验不生成图谱节点或图谱边。

可以支持的最强主张取决于上游证据：

- 实验 02 未完成时，结果只能描述合成 Simulator benchmark 上的重建表现；
- 若已有 Simulator 状态忠实度与安全性证据，结果可在已验证范围内支持 Simulator 中介的 Agent 比较；
- 声称方法可迁移到真人用户前，必须完成匹配的真人 episodes。

## 2. 研究问题

| 编号 | 研究问题 |
| --- | --- |
| RQ-A1 | 在相同轮次预算下，各 Agent 重建完整隐藏 Knowledge Map 的准确性如何？ |
| RQ-A2 | 自适应问题选择是否优于非自适应或随机选择？ |
| RQ-A3 | 显式不确定性与证据累积是否改善校准并减少无依据推断？ |
| RQ-A4 | 增益如何随领域、图谱区域、掌握度层、轮次预算与模型配对变化？ |
| RQ-A5 | 各方法在准确性、延迟、token、模型调用与失败率上有何权衡？ |

## 3. 确证性假设

- **H-A1：** 在图谱、隐藏 map、轮次预算、provider/model 家族、Simulator 条件和重试策略相同时，ECDA 的配对 Episode Mastery Distance 低于 Simple LLM Agent。
- **H-A2：** 当带版本专家题库被绑定到 manifest 后，自适应题库选择与 ECDA 的误差低于带 seed 的随机选择。
- **H-A3：** ECDA 减少缺失预测或无依据推断，且主要掌握度距离没有具有实际意义的退化。
- **H-A4：** 可报告的增益不能只出现在一个领域，或一个 Tested Agent/Simulator 模型配对中。

H-A2 延后执行，直至题库 identity、version 与内容 hash 成为不可变 episode contract 的组成部分。

## 4. 前置条件与冻结输入

确证性运行前必须冻结：

- reviewed graph 的版本与哈希；
- reviewed map ID、map 分层与排除规则；
- Simulator workflow、provider/model、prompt 版本、条件、temperature 与重复 seed 策略；
- Tested Agent 代码版本、provider/model、prompt 版本、temperature 与重试策略；
- agent kind、轮次预算、scoring profile 与 episode identity；
- 主要对比、实际效应阈值、样本量规则、bootstrap 分块与多重比较族；
- 失败、fallback、取消、重启与缺失运行的处理方案。

所有比较条件必须获得相同的可见图谱和等价的隐藏 map/Simulator 设置。

新增 Agent 条件时，必须创建新的不可变 episode ID，不得修改已完成 episode。

## 5. 实验条件

### 5.1 当前可执行的核心比较

| 编号 | Agent | 当前状态 | 角色 |
| --- | --- | --- | --- |
| C0 | Simple LLM Agent | 已实现 runtime kind | 当前直接分类基线 |
| C1 | Evidence-Calibrated Diagnostic Agent | 已实现实验性 runtime kind | 主要研究候选方法 |

两个条件使用相同的 Tested Agent protocol、working-map 工具、visibility boundary、finalization path 与 scoring profile。

### 5.2 延后的题库策略比较

| 编号 | 策略 | 状态 |
| --- | --- | --- |
| B1 | 固定专家题库顺序 | 已有代码组件；缺少正式绑定 |
| B2 | 带 seed 的随机题库 | 已有代码组件；缺少正式绑定 |
| B3 | 覆盖度贪心题库 | 仅有设计 |
| B4 | LLM 题库选择器 | 仅有设计 |

只有在不可变 reviewed question bank 已存储、验证，并被每个 Episode Manifest 引用后，这些条件才可进入确证性分析。

### 5.3 诊断上限与负对照

可以加入不提问的被动重建条件，以衡量对话本身的价值。

Oracle 只能作为离线 sanity-check 上限，不能作为 Tested Agent，也不能进入公平性主张。

## 6. 实验设计

采用配对区组设计。每个 Agent 条件使用相同领域、reviewed graph、隐藏 map 分层、轮次预算、Simulator 条件和 seed 日程。

不可变 Evaluation Episode 是 runtime 单位。独立的科学分析单位是隐藏用户/map 样本，不是单个 turn、node 或重复模型 seed。

重复 seed 用于估计随机波动，不能视为独立用户，也不能挑选 best-of-seed 结果。

建议区组因素：

- benchmark 领域与图谱版本；
- 隐藏 map 掌握度分布层；
- 轮次预算；
- Tested Agent 模型家族；
- Simulator 模型家族与 seed 日程。

## 7. 主要结果

主要结果是 `squared_mastery_distance_v1` 下的全图平均 Episode Mastery Distance。

对图谱节点 \(n\)，真实等级 \(y_n \in \{0,\ldots,5\}\)，提交预测 \(\hat y_n\)：

\[
d_n =
\begin{cases}
(\hat y_n-y_n)^2, & \hat y_n \neq \text{unknown},\\
36, & \hat y_n = \text{unknown}.
\end{cases}
\]

\[
D_{\mathrm{episode}}=\frac{1}{|V|}\sum_{n\in V}d_n.
\]

数值越低越好。Episode 图谱中的全部节点均参与评分。

## 8. 次要结果

- 掌握度完全准确率与误差不超过一级的准确率；
- 带符号掌握度误差，以及高估/低估率；
- 缺失预测率；
- 无依据推断率；
- 有直接证据支持的预测 precision 与 recall；
- 条件提供六级 belief 时的 Brier score 与校准误差；
- 随 turn 变化的节点和图簇覆盖度；
- 有效中间投影可用时，掌握度误差关于 turn 的曲线下面积；
- 问题数、模型调用数、输入/输出 token、延迟、估算成本、解析失败、重试耗尽、fallback、取消与重启率；
- 在预注册子集上，对问题连贯性和证据支持度进行盲法人评。

准确性、校准、证据支持与成本必须分别报告。不得在看到结果后调整一个复合排行榜分数。

## 9. 消融实验

优先保留一个小型确证性消融族：

| 编号 | 改动 | 目标机制 |
| --- | --- | --- |
| A1 | 用纯分类状态替代 posterior state | 显式不确定性 |
| A2 | 用最新回答覆盖替代累积更新 | 纵向证据 |
| A3 | 移除图结构杠杆项 | 图感知选择 |
| A4 | 移除覆盖项 | 全图覆盖目标 |
| A5 | 用 LLM 直接选择替代多候选 utility | 提议与选择的分解 |
| A6 | 移除 evidence note 与 turn reference 约束 | 可追溯性与无依据推断 |

其他消融默认为探索性分析。若希望进入确证性分析，必须在观察最终数据前加入预注册。

## 10. 样本量流程

1. 运行工程 fixture，验证产物与失败处理。
2. 冻结一个不进入确证性推断的 pilot 集。
3. 估计主要 C1 减 C0 配对对比的方差。
4. 在最终运行前确定最小实际有意义改进。
5. 在计划的区组结构下进行配对 power analysis。
6. 冻结 episode 数、seed、停止规则与排除标准。

在 pilot 方差与运行失败率未知前，不预设一个缺乏依据的固定样本数。

## 11. 统计分析

- 将节点聚合为预注册的 episode 级主要分数；
- 在区组内估计配对条件差；
- 对各领域内的 map 样本使用层级或区组 bootstrap；
- 报告配对均值、中位数、标准化效应、95% 置信区间与完整 episode 分布；
- 对确证性的 ECDA 对基线比较族使用 Holm 校正；
- 报告领域与模型家族交互，但不能用它们替代主要对比；
- 在运行报告中保留失败与 fallback，并只应用预注册的推断处理。

若一个 map 使用多个 Simulator seed，应先在 map-condition 单元内聚合，或在模型中显式表示重复测量结构。

## 12. 泄漏与公平性检查

分析前必须验证 Tested Agent payload 与持久化 trace 不含 hidden map、Profile Context、Simulator debug trace、answer blueprint、hidden evidence 或 scoring input。

被比较 Agent 必须使用相同的可见图谱、轮次预算、Simulator 日程、finalization contract、评分代码与重试上限。

模型调用与 token 差异应作为结果测量，而不能在事后静默抹平。

## 13. 结果产物约定

正式 runtime 产物写入：

```text
experiments/03_agent_reconstruction/results/runs/{run_id}/
```

运行目录包含不可变 manifest 快照、已提交 turns、可见 transcript、最新 working map、Agent tool trace、最终输出与 scoring report。

成功完成后会移除仅用于恢复的 checkpoint 状态。

聚合报告必须记录代码版本、产物哈希、模型名、provider 日期、prompt、条件 ID、全部排除项与每次失败运行。

## 14. 决策规则与解释

只有同时满足以下条件，ECDA 才能从实验候选提升为可报告方法：

- 在主要全图误差上，相比 Simple LLM baseline 有统计上和实际上有意义的改进；
- 安全性或证据支持没有实质退化；
- 结果不依赖一个无法解释的单领域或单模型失败模式。

若主要对比不成立，应如实报告零结果或负向结果。次要自然度、某个有利 seed 或单一领域切片不能挽救主要主张。

若上游 Simulator 有效性仍不完整，结论必须标为“合成 benchmark 上的重建表现”，不得外推到真人用户。
