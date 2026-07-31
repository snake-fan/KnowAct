# 实验 01 材料

[English](README.md)

本目录使用离线 HTML 收集评审，并只导入/导出 JSON。旧的 CSV 表单不再是执行材料。

## 文件

- `review_pages/economy_kg_review.html`：Economy candidate KG 独立评审；
- `review_pages/islp_kg_review.html`：ISLP candidate KG 独立评审；
- `review_pages/ostep_kg_review.html`：OSTEP candidate KG 独立评审；
- `review_pages/compare_and_confirm.html`：导入两份同图谱完整评审 JSON，
  计算 raw agreement 与 Cohen's kappa，处理触发项并导出确认 JSON；
- `schemas/kg_review_submission.schema.json`：评审提交契约；
- `schemas/kg_review_confirmation.schema.json`：比对与确认契约；
- `../tools/build_review_pages.py`：从三个固定 candidate runs 和 source metadata
  重新生成四个页面；
- `../templates/`：离线页面模板。

## 独立评审

1. 将对应 domain 的 HTML 页面分别交给两名合格评审者。
2. 评审者在提交前不得查看另一人的判断、Agent trace 或既有内部 AI 评审。
3. 页面会在当前浏览器本地保存草稿；评审者可随时导出 `status=draft` JSON。
4. 只有四个评审者字段（`reviewer_id`、`role`、`experience_band`、
   `introduction`）、全部节点、边、50 项代表性任务和总体决定通过校验后，
   页面才允许导出 `status=complete` JSON。
5. 去标识化 ID 可使用 `R1`、`R2`；不要写入姓名。

## 比对与确认

1. 打开 `review_pages/compare_and_confirm.html`。
2. 导入同一图谱的两份 `status=complete` 评审 JSON。
3. 页面会校验 schema、完整性、reviewer ID、graph fingerprint 与条目集合。
4. 页面计算节点和边决定的原始一致率与 Cohen's kappa，并定位受控字段分歧。
5. 逐项处理分歧、缺陷、修改、删除和覆盖不足触发项。
6. 导出 `knowact.kg_review_confirmation.v3` JSON。

确认结果的 `promotion_readiness.status` 只可能是：

- `not_approved`；
- `edits_required`；
- `ready_for_structural_validation`。

即使是最后一种状态，`promotion_ready` 仍固定为 `false`；仓库结构验证和显式
benchmark-author promotion 仍是独立步骤。

## 重新生成与验证

在仓库根目录运行：

```bash
python3 experiments/01_kg_scientific_validity/tools/build_review_pages.py
python3 experiments/01_kg_scientific_validity/tools/build_review_pages.py --check
```

生成器中的三条 run binding 是显式常量。新增 candidate run 不会静默替换已开始评审
的输入；切换输入时必须明确更新 binding、重新生成页面并检查新哈希。

已完成的评审 JSON 包含评审者角色、经验区间和简短个人介绍。可识别原件必须保存在
Git 之外；只有发布方案允许时，才归档去标识化副本。
