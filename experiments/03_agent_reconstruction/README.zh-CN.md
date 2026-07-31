# 实验 03：Agent 知识地图重建

[English](README.md)

## 目的

本实验衡量 Tested Agent 能否在可见 reviewed Knowledge Graph 上，通过有限轮诊断对话，准确重建隐藏的用户 Knowledge Map。

## 状态

| 组成部分 | 状态 |
| --- | --- |
| 实验设计 | 已准备 |
| 当前 Agent 实现 | Simple LLM 与实验性 ECDA 已可用 |
| 正式题库基线 | 延后，等待不可变题库绑定 |
| 实验清单 | 未冻结 |
| 运行 | 未开始 |
| 实验结果 | 无 |

## 内容

- [`design/experimental_design.zh-CN.md`](design/experimental_design.zh-CN.md)：中文预注册式设计，包括假设、配对比较、指标、样本量流程、分析与接纳门槛；
- [`design/legacy_design_notes.md`](design/legacy_design_notes.md)：中文历史设计备注，仅保留用于追溯；
- [`materials/README.zh-CN.md`](materials/README.zh-CN.md)：运行代码前必须冻结的产物清单；
- [`results/README.zh-CN.md`](results/README.zh-CN.md)：生成产物布局与当前结果状态；
- `runtime/`：Episode Run Queue 使用且被 Git 忽略的队列控制状态。

更完整的方法证据位于 [`../../docs/research/tested_agent_knowledge_map_reconstruction/`](../../docs/research/tested_agent_knowledge_map_reconstruction/README.md)。
