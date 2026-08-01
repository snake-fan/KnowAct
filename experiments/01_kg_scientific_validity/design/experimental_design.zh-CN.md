# 三领域 Candidate Knowledge Graph 专家评审实验

[English](experimental_design.md)

> 状态：协议、三个独立评审 HTML 和 JSON 比对/确认页面已准备；尚未记录任何
> 专家评审结果。

## 目的与主张边界

本实验分别对 `Economy`、`ISLP` 和 `OSTEP` 的固定 candidate graph 做内容有效性
检查，回答：

> 合格领域专家是否认为图谱中的节点有来源支持、属于声明范围、可用于诊断并具有
> 可区分的 L0--L5 量规，同时认为图谱中的边具有合理的关系类型、方向与依据？

实验不比较图谱生成方法，不相对于参考本体估计 extraction recall，也不把 candidate
graph 称为 benchmark ground truth。每个 domain 的可报告结论必须分别给出，不能仅
因三个 domain 使用同一 workflow 就合并为跨领域有效性结论。

## 冻结评审包

| Domain | Candidate run | Nodes | Edges | Tasks |
| --- | --- | ---: | ---: | ---: |
| Economy | `20260730T093034765328Z` | 22 | 20 | 50 |
| ISLP | `20260730T085835823437Z` | 21 | 29 | 50 |
| OSTEP | `20260730T091621837090Z` | 24 | 28 | 50 |

每个 HTML 评审包内嵌：

- 对应 `candidate_nodes.json` 与 `candidate_edges.json`；
- source title、citation、scope、50 项 representative tasks 和 excluded topics；
- candidate nodes、candidate edges、source metadata 与 source content 的 SHA-256；
- 基于上述 binding 确定性派生的 `graph_fingerprint`。

评审输入是 candidate artifacts。只有后续独立评审、JSON 仲裁、必要修改、重新冻结、
结构验证和显式 benchmark-author promotion 全部完成后，才可能发布 reviewed graph。

## 评审者

每个 domain 招募两名独立评审者。评审者至少满足一项：

- 教授或助教过直接覆盖该 domain 声明范围的大学课程；
- 在该范围内开展过研究或专业实践；
- 具有高级学位，并有直接相关的课程训练与评价经验。

评审者不得参与被分配 candidate graph 的生成、编辑、verifier 判断或 promotion。
项目负责人在分配前筛查其他项目关系，不为此增加专家资料字段。导出数据只保留
`reviewer_id`、`role`、`experience_band`、`introduction`，并使用 `R1`、`R2`
等 ID，不记录姓名。

一名评审者可以评审多个 domain，但必须分别满足资格要求；每个 domain 仍需两份独立
完整提交。只有 R1 与 R2 查看彼此完成的判断后仍无法解决条目时，才引入第三名合格
评审者。

## 独立评审流程

### 1. 打开对应 HTML

评审者打开下列文件之一：

- `../materials/review_pages/economy_kg_review.html`
- `../materials/review_pages/islp_kg_review.html`
- `../materials/review_pages/ostep_kg_review.html`

页面可离线运行，在浏览器本地保存草稿，并支持导出草稿 JSON。两份独立提交完成前，
评审者不得讨论条目或互相查看 JSON。

### 2. 评审全部节点

评审者查看 node name、definition、source locators、diagnostic goal、L0--L5 levels、
diagnostic signals 与 simulator behavior。

| 字段 | 允许值 |
| --- | --- |
| `scope_fit` | `in_scope`、`boundary`、`out_of_scope` |
| `granularity` | `appropriate`、`too_broad`、`too_narrow`、`mixed` |
| `diagnostic_usefulness` | `adequate`、`minor_issue`、`major_issue` |
| `rubric_quality` | `adequate`、`minor_issue`、`major_issue` |
| `decision` | `accept`、`edit`、`reject` |

`edit` 必须填写最小必要修改与理由；`reject` 必须填写理由。

### 3. 评审全部边

| 字段 | 允许值 |
| --- | --- |
| `relation_validity` | `valid`、`uncertain`、`invalid` |
| `type_correct` | `yes`、`no`、`uncertain` |
| `replacement_type` | 空或 `part_of`、`prerequisite_for`、`supports`、`contrasts_with` |
| `direction_correct` | `yes`、`no`、`not_applicable`、`uncertain` |
| `provenance_class` | `source_explicit`、`source_entailed`、`expert_pedagogical_extension`、`unsupported` |
| `decision` | `accept`、`edit`、`delete` |

`type_correct=no` 时必须选择替代类型。`contrasts_with` 的方向必须是
`not_applicable`，其他关系不得使用该值。`edit` 必须填写精确修改与理由；`delete`
必须填写理由。仅仅“有关联”不足以保留一条边。

### 4. 检查 50 项代表性任务

每名评审者对 metadata 中冻结的全部 50 项 representative tasks 逐项评价：

- `sufficient`
- `partial`
- `insufficient`

`partial` 或 `insufficient` 必须记录必要缺失或冗余内容及理由。该步骤是 bounded
scope check，不是相对于参考本体的正式召回率估计。

随后给出总体图谱决定：

- `approve`
- `approve_after_edits`
- `do_not_approve`

### 5. 导出完整评审 JSON

页面只有在以下内容全部完成后才允许导出 `status=complete`：

- 评审者 ID、角色、经验区间和个人介绍四个字段；
- 每个节点和边的受控字段与条件字段；
- 全部 50 项 coverage review；
- 总体图谱决定。

输出 schema 为 `knowact.kg_review_submission.v3`。JSON 内保留完整 graph binding 与
fingerprint；不能仅凭文件名确定它评审了哪张图。

## JSON 比对与仲裁

在两份独立完整提交后，打开
`../materials/review_pages/compare_and_confirm.html` 并导入 R1、R2 JSON。页面拒绝：

- 草稿或 validation 未完成的提交；
- 不属于当前三个冻结包的 graph fingerprint；
- 两份不同 fingerprint 的提交；
- 相同 reviewer ID；
- node、edge 或 task 条目集合/顺序不匹配。

页面分别报告：

- 节点 `decision` 的 raw agreement 与 Cohen's kappa；
- 边 `decision` 的 raw agreement 与 Cohen's kappa；
- task coverage 的完全一致数；
- 每个受控字段的分歧数；
- 需要仲裁的条目数。

以下任一情况触发逐项确认：

- 受控字段不一致；
- 任一 `unsupported`、`out_of_scope`、`major_issue`、`invalid`；
- 任一 `edit`、`reject` 或 `delete`；
- 任一 `partial` 或 `insufficient` coverage；
- 任一 `approve_after_edits` 或 `do_not_approve`。

每个触发项记录最终决定、精确修改/处理和仲裁理由。比对页面导出
`knowact.kg_review_confirmation.v3`，并保存两份输入 JSON 的 SHA-256。

## 接纳与 promotion 边界

确认 JSON 的 `promotion_readiness.status` 采用三个状态：

1. `not_approved`：总体最终决定为 `do_not_approve`；
2. `edits_required`：存在修改、删除、拒绝、覆盖问题或条件批准；
3. `ready_for_structural_validation`：所有最终节点/边均无修改接受、所有任务均覆盖充分，
   且总体决定为 `approve`。

确认页面不执行 promotion，并固定输出 `promotion_ready=false`。

- `edits_required` 时，必须修改 candidate artifacts，重新生成带新 SHA-256 与
  fingerprint 的评审包，并按修改范围完成复核；旧确认不能证明新文件已经被评审。
- `ready_for_structural_validation` 时，仍必须运行仓库图结构验证，再由 benchmark author
  显式调用不可覆盖的 promotion 流程。
- 发布后的 reviewed graph 如需修订，必须使用新 version，不得覆盖旧版本。

不设置任意最低 kappa 阈值。raw agreement 与 kappa 描述评审可靠性；是否可继续取决于
仲裁完成、有效性缺陷已解决、artifact binding 未漂移以及结构验证通过。

## 研究输出

每个 domain 分别归档：

- 两份去标识化完整评审 JSON；
- 一份完整确认 JSON；
- 输入与最终 candidate/reviewed artifact hashes；
- 结构验证命令与结果；
- 适用时的新 graph version；
- 一份完成的结果摘要。

空白页面、schema、草稿或生成器通过测试均不构成专家评审结果。
