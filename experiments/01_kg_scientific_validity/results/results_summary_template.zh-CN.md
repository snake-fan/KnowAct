# Knowledge Graph 专家评审结果

[English template](results_summary_template.md)

> 状态：未填写模板。本文档不代表已经获得任何专家评审结果。每个 domain 单独复制并填写。

## 冻结输入

- Domain：`[Economy | ISLP | OSTEP]`
- Candidate run：`[run_id]`
- Graph fingerprint：`[sha256:...]`
- Candidate nodes SHA-256：`[hash]`
- Candidate edges SHA-256：`[hash]`
- Source metadata SHA-256：`[hash]`
- Source content SHA-256：`[hash]`
- 节点 / 边 / 代表性任务：`[N] / [E] / 50`
- 完整评审 JSON：`[R1 file + SHA-256]`、`[R2 file + SHA-256]`
- 确认 JSON：`[file + SHA-256]`

## 评审者信息

| 评审者 ID | 角色 | 经验区间 | 个人介绍 |
| --- | --- | --- | --- |
| R1 |  |  |  |
| R2 |  |  |  |

## 节点评审

| 指标 | R1 | R2 | 最终确认 |
| --- | ---: | ---: | ---: |
| Accept，n（%） |  |  |  |
| Edit，n（%） |  |  |  |
| Reject，n（%） |  |  |  |
| 超出范围，n |  |  |  |
| 重大诊断或量规问题，n |  |  |  |

- Node decision raw agreement：`[值]`
- Node decision Cohen's kappa：`[值]`

| 受控字段 | R1 与 R2 分歧数 |
| --- | ---: |
| `scope_fit` |  |
| `granularity` |  |
| `diagnostic_usefulness` |  |
| `rubric_quality` |  |
| `decision` |  |

## 边评审

| 指标 | R1 | R2 | 最终确认 |
| --- | ---: | ---: | ---: |
| Accept，n（%） |  |  |  |
| Edit，n（%） |  |  |  |
| Delete，n（%） |  |  |  |
| 关系无效，n |  |  |  |
| 类型错误，n |  |  |  |
| 方向错误，n |  |  |  |

- Edge decision raw agreement：`[值]`
- Edge decision Cohen's kappa：`[值]`

| 受控字段 | R1 与 R2 分歧数 |
| --- | ---: |
| `relation_validity` |  |
| `type_correct` |  |
| `replacement_type` |  |
| `direction_correct` |  |
| `provenance_class` |  |
| `decision` |  |

## 覆盖度

- 50 项任务 coverage 完全一致数：`[数量]/50`
- 最终 `sufficient` / `partial` / `insufficient`：`[n] / [n] / [n]`
- 总体图谱决定：`R1=[值]`、`R2=[值]`、`最终=[值]`
- 需要仲裁的条目：`[数量]`
- 未解决条目：`[必须为 0]`

## 确认、修改与 promotion

- `promotion_readiness.status`：`[not_approved | edits_required | ready_for_structural_validation]`
- 节点修改/拒绝：`[摘要]`
- 边修改/删除：`[摘要]`
- 范围处理：`[摘要]`
- 修改后重新冻结 fingerprint：`[适用时填写]`
- 结构验证：`[命令与结果]`
- 最终 graph version：`[未 promotion 或版本]`
- 最终 nodes / edges SHA-256：`[hash] / [hash]`

## 可用于论文的表述

> 两名合格且独立的 `[domain]` 评审者分别评估了固定 candidate graph 的全部
> `[N]` 个节点、`[E]` 条边和 50 项代表性任务。节点和边总体决定的原始一致率为
> `[x]` 与 `[y]`，Cohen's kappa 为 `[kx]` 与 `[ky]`。所有触发项均通过绑定两份
> 输入 SHA-256 的 JSON 确认流程处理；最终 reviewed graph 仅在必要修改、重新冻结
> 和结构验证后发布。

## 主张边界

本评审只支持该 domain 声明 aspect 与代表性任务范围内的内容有效性。它不能证明
生成方法优越、相对于本体的召回率完备，或 L0--L5 在不同领域具有普遍心理测量效度。
