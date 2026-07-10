# Workflow 7: Tested-Agent Decision and Reconstruction

## 目标与位置

Tested Agent 是被评估对象。它在可见 graph 上选择诊断问题，解读 Simulator 的可见回答，维护自己的不确定 working map，并在预算耗尽后提交完整 reconstructed map。

```text
visible graph + prior visible transcript + working map
-> choose one diagnostic question -> receive observation
-> update working map -> repeat within budget
-> submit final reconstructed map with visible evidence references
```

## 设计亮点

### 将决策与隐藏 truth 隔离

agent protocol/input 只包含 Tested-Agent-visible context。Simple LLM agent、fixed-question 和 random-question baseline 都必须穿过同一接口；实现不能读取 hidden map、profile context、simulator debug trace 或 scoring data。

### Working map 是行动工具，不是评分提交

agent 可以在每轮维护带假设和不确定性的 working map，用它选择下一问；它是可替换的内部决策状态。真正被评分的是最后一次完整 `Reconstructed Knowledge Map`，避免把过程表示格式强加给所有被测方法。

### 语义工具而非隐藏字段访问

working-map tools 按 node、可见 evidence 和约束提供操作，帮助 agent 做主动诊断，但不提供 simulator-only evidence 或 ground truth labels。这样既支持有 ToM 的策略，也保持同一信息预算。

### 全图、显式缺失预测

final submission 必须覆盖 episode graph 的每个 node。`unknown` 表示 missing prediction，而非低掌握度 L0；这让保守不猜与正确诊断在评分中有清楚、可比较的后果。

## 关键边界

- v1 的 agent 不教学、不改变用户隐藏状态；问题应服务于 diagnosis。
- observation 只有可见回答和粗 metadata，不能利用 benchmark-author preview 的 grounded-node highlighting。
- agent trace 可用于实验分析，但不是 simulator 或 scoring 的隐藏输入。
