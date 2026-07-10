# Workflow 8: Structured Scoring and Reporting

## 目标与位置

Scoring 在 episode 完成后，确定性比较 final reconstructed map 和 hidden ground-truth map，并形成可复现的结构化 report。它不参与 simulator 答案生成，也不向 Tested Agent 暴露中途反馈。

```text
validated manifest + hidden reviewed map + final reconstruction
-> reconstruction validation -> node-wise comparison
-> aggregate metrics -> score report -> experiment/report artifacts
```

## 设计亮点

### 固定的主评分语义

v1 使用 manifest 固定的 `squared_mastery_distance_v1`：对 episode graph 的所有节点计算 mastery distance 的均值，越低越好。它避免 per-episode 临时调权，使结果能跨 run 直接比较。

### 缺失不是 L0

提交的 `unknown` 视为 Missing Prediction，并采用最大距离惩罚 `36`，不会被解释为“完全不会”。这分别度量了 agent 的覆盖能力和它对低掌握度的判断能力。

### 支持证据单独报告

除主分数外，report 包含 missing prediction rate 与 unsupported inference rate。重建 map 的 evidence refs 必须引用 Tested Agent 可见的证据；因此“猜对”与“依据可见互动得出结论”可被区分，而不会污染主 mastery comparison。

### schema-first、可审计输出

scoring 先验证 reconstruction 对图 coverage、mastery 值、evidence visibility 和 manifest binding 的一致性，再产生 node-level comparison 与 aggregate report。报告、输入 artifact identities 和 run output 可回溯，但 hidden evidence 不进入 Tested Agent 可见结果。

## 关键边界

- v1 只评 final reconstruction，不把逐轮 working map 或思维链作为 primary score。
- scoring profile 不允许由单个 episode 请求覆盖。
- report 面向 benchmark author/研究分析；运行中不得反向泄漏给被测 agent。
