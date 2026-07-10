# Workflow 2: Graph Review and Promotion

## 目标与位置

该流程把一个保存的 candidate graph run 转为正式 `Authored Knowledge Graph` version。它是人工判断与 runtime 数据之间的闸门。

```text
candidate graph run -> benchmark-author review -> revalidation
-> graphs/{graph_version}/authored_nodes.json + authored_edges.json + graph_manifest.json
```

## 设计亮点

### 人工确认是明确动作

agent 生成只提供可审核建议。promotion 必须由 benchmark author 显式发起，确保来源覆盖、节点粒度、rubric 可诊断性和边关系能由研究者判断，而不将模型输出误当作 benchmark truth。

### 发布前再次校验

promotion 不信任历史运行结果：再次校验 node id、edge endpoint、edge type、source locator 和图结构。这样候选 run 的文件损坏或过期实现不会绕过 reviewed 边界。

### 版本不可变，引用稳定

发布后 graph version 永不覆盖；更正要发布新 version。后续 map manifest 和 episode manifest 按 graph version 绑定，因此老实验仍能按原图复现。

## 关键边界

- runtime 只经 reviewed loader 读取 `graphs/{version}`，绝不从 candidate graph run 读取。
- promotion 复制经过验证的 node/edge list，并生成最小 `graph_manifest.json`；不将 agent trace 变成正式 benchmark data。
- graph review 只审核客观知识结构，不包含任意用户的 mastery 或 evidence。
