# 实验 01：知识图谱科学有效性

[English](README.md)

## 目的

本实验评估当前生成的三张 Candidate Knowledge Graph：`Economy`、`ISLP` 和
`OSTEP`。合格领域专家逐项判断节点的范围适配、诊断价值和 L0--L5 量规质量，
以及边的关系有效性、类型、方向和依据。

实验只支持声明范围内的内容有效性主张。它不能证明当前生成方法优于其他方法，
也不能证明图谱穷尽覆盖整个领域。

## 当前状态

| 组成部分 | 状态 |
| --- | --- |
| 实验设计 | 已重新绑定到三个现存 candidate runs |
| 独立评审页面 | 已生成三份离线 HTML |
| 评审数据格式 | `knowact.kg_review_submission.v3` JSON |
| 比对与确认 | 由两份完整评审 JSON 驱动，并导出 `knowact.kg_review_confirmation.v3` JSON |
| 专家评审 | 未运行 |
| 实验结果 | 仅有空白模板 |

## 冻结评审输入

| Domain | Candidate run | Nodes | Edges | Representative tasks | 评审页面 |
| --- | --- | ---: | ---: | ---: | --- |
| Economy | `kg_metadata_v1_economy_20260730_contract_retry_v6` | 22 | 20 | 50 | [`economy_kg_review.html`](materials/review_pages/economy_kg_review.html) |
| ISLP | `kg_metadata_v1_islp_20260730_evidence_v2` | 21 | 29 | 50 | [`islp_kg_review.html`](materials/review_pages/islp_kg_review.html) |
| OSTEP | `kg_metadata_v1_ostep_20260730_robust_v2` | 24 | 28 | 50 | [`ostep_kg_review.html`](materials/review_pages/ostep_kg_review.html) |

这些输入仍是 candidate artifacts，不是 reviewed benchmark graph。每份页面内嵌节点、
边、scope、来源 metadata 以及文件 SHA-256，并用一个 `graph_fingerprint` 固定绑定。

## 执行入口

- [`design/experimental_design.zh-CN.md`](design/experimental_design.zh-CN.md)：
  评审者资格、独立评审、受控字段、JSON 比对、仲裁与接纳规则；
- [`materials/README.zh-CN.md`](materials/README.zh-CN.md)：页面、JSON Schema、
  生成器与执行步骤；
- [`materials/review_pages/compare_and_confirm.html`](materials/review_pages/compare_and_confirm.html)：
  导入同一图谱的两份完整评审 JSON，计算一致性并导出确认 JSON；
- [`results/results_summary_template.zh-CN.md`](results/results_summary_template.zh-CN.md)：
  未填写的聚合结果模板。

## 数据流

```text
冻结 Candidate KG HTML
  -> R1 完整评审 JSON
  -> R2 完整评审 JSON
  -> JSON 比对与仲裁
  -> 确认 JSON
  -> 必要修改与重新冻结
  -> 结构验证
  -> 显式 benchmark-author promotion
```

评审和确认阶段不使用 CSV。确认 JSON 也不会自动执行 promotion：若有修改、删除、
拒绝或范围问题，必须先更新 candidate artifacts，重新生成带新哈希的页面，并按协议
完成必要复核。
