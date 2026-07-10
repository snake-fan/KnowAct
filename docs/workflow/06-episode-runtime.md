# Workflow 6: Evaluation Episode Runtime

## 目标与位置

Episode Runtime 将审核后的 graph、hidden map 和固定规则绑定成一个可执行、可复现的评估单元，并协调 Tested Agent 与 Simulator 的多轮交互。

```text
reviewed graph + reviewed map + max_turns
-> validated Evaluation Episode Manifest -> Runtime Episode Registry
-> start run -> repeated agent decision / simulator turn
-> final reconstruction -> scoring report + persisted run artifacts
```

## 设计亮点

### manifest 是唯一的实验绑定点

`Evaluation Episode Manifest` 固定 graph version、hidden map、turn budget、interaction rule 和 `squared_mastery_distance_v1`。注册时由服务写入固定 v1 规则并校验 reviewed-artifact binding，拒绝同名 episode；它避免把实验关键配置散落在请求参数或 prompt 中。

### runtime 只装配，不重写领域规则

runtime 依赖 core、validation、storage、simulator、agents 和 scoring：它负责顺序、重试和持久化，而不自行定义 graph/map 语义、模拟策略或分数。这使单轮 simulator 与正式 episode 可以共享契约，又不会形成平行实现。

### 分层可见性

运行时向 Tested Agent 提供 reviewed graph、可见对话和其 own working map；hidden map、profile context、answer blueprint、simulator traces 和 scoring internals 留在受限数据路径。公开 transcript 同样只保留可见 turn 数据。

### 显式预算与终局提交

每 turn 只能有一个 Diagnostic Question，`max_turns` 是明确停止条件。run 结束后评分的是 final reconstructed map，不是内部思考或逐轮草稿，令不同 agent 的比较边界一致。

## 关键边界

- episode runtime 永远不读取 candidate graph/map。
- run id 不覆盖；run artifacts 在 `experiments/runs/{run_id}/` 下按职责保存。
- 单轮 `/api/simulator/turn` 是独立 preview，不可被当成隐式 episode runtime。
