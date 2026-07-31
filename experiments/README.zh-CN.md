# KnowAct 实验目录

[English](README.md)

`experiments/` 是可执行实验协议、实验材料、运行产物与结果报告的唯一正式归档位置。文献综述与方法依据仍保存在 `docs/research/`。

## 实验总览

| 编号 | 实验 | 设计 | 材料 | 结果 |
| --- | --- | --- | --- | --- |
| 01 | [专家验证知识图谱的科学有效性](01_kg_scientific_validity/README.zh-CN.md) | 已绑定 Economy、ISLP 与 OSTEP candidate graphs | 离线 HTML + JSON 评审与确认包已准备 | 未运行 |
| 02 | [基于真人数据验证 SAGE Simulator](02_simulator_human_validity/README.zh-CN.md) | 已准备 | 已准备，待专家审核与预测试 | 未运行 |
| 03 | [测试 Agent 的知识地图重建能力](03_agent_reconstruction/README.zh-CN.md) | 已准备 | 目前仅有冻结清单 | 未运行 |

## 目录约定

每个实验包含三类内容：

- `design/`：面向预注册的研究问题、假设、流程、分析方案与主张边界；
- `materials/`：执行协议所需的量表、题集、清单、脚本与数据字典；
- `results/`：结果模板、聚合分析、报告与生成的运行产物。

运行时控制状态不属于科学结果。因此，实验 03 将队列状态放在 `03_agent_reconstruction/runtime/`，与 `results/` 相邻但相互分离。

## 状态与证据规则

空白模板或已实现的代码路径不等于实验结果。每个实验的 README 都必须分别标明设计、材料、数据收集、分析和报告是否完成。

三个实验支持的主张不同：

1. 实验 01 评估冻结 reviewed graph 的内容有效性。
2. 实验 02 评估 Simulator 的状态忠实度、安全性，以及相对于留出真人数据的代理有效性。
3. 实验 03 在固定交互预算下，衡量 Tested Agent 重建隐藏用户 Knowledge Map 的准确性。

实验 02 完成前，可以先运行实验 03 的工程冒烟测试。但此时科学结论只能描述合成 benchmark 上的表现，不能外推到真人用户。

## 双语与执行材料

叙述性文档使用 `README.md` 与 `README.zh-CN.md`，或 `name.md` 与 `name.zh-CN.md` 并行维护。

JSON 等结构化执行材料只保留一份权威文件。中文说明解释字段、流程与数据边界，但不会复制数据模板，以免两个版本出现不一致。

## 数据管理

不得提交参与者身份信息、同意记录、原始真人回答或私有 Profile Context。此类数据应存入受访问控制的 `private/` 或 `raw/` 目录；这些路径已被 Git 忽略。

只有在满足研究同意、伦理审查与发布方案后，才可提交去标识化的聚合结果。模型凭据只能保存在仓库根目录的 `.env` 中，不得写入实验清单或报告。

## 生成的运行产物

实验 03 的正式 Episode Run 产物写入：

```text
experiments/03_agent_reconstruction/results/runs/{run_id}/
```

持久化队列控制文件写入：

```text
experiments/03_agent_reconstruction/runtime/run_queue.json
```

以上路径取代旧的 `experiments/runs/` 与 `experiments/runtime/` 布局。
