# 实验 02 结果

[English](README.md)

尚未收集真人数据，也没有 Simulator 个人一致性的实证结果。

自动化流程把每个可恢复会话写入：

```text
private/sessions/{session_id}/session.json
```

参与者对 Candidate Map 的逐节点修订轨迹写入：

```text
private/map_reviews/{map_id}.json
```

`private/` 已被 Git 忽略。会话包含题库版本、语言、抽样 seed、20 题顺序、真人回答、
Simulator 回答、自评和 `blind_review_status`。它不等同于专家盲评结果。

后续专家盲评必须生成独立的去标识化 artifact，使用随机展示标识符，并隔离
participant code、Profile、Map、自评和 debug trace。原始会话不得被盲评结果覆盖。

只有在应用冻结的排除规则、缺失数据处理和分析方案后，才可在本目录提交
去标识化聚合报告。
