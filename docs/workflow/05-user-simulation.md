# Workflow 5: SAGE Single-Turn User Simulation

## 目标与位置

Simulator 使用 **SAGE（Scoped Answer Generation from Epistemic State）**，
把 hidden reviewed map 转换为自然、有限、作用域受限的用户回答。当前单轮服务是
runtime 前的可测试边界：无服务端 session，也不读取 episode manifest。

```text
Diagnostic Question + visible dialogue
-> question grounding on reviewed graph
-> direct-node hidden context construction
-> answer blueprint validation -> answer generation -> parse/retry
-> visible answer or safe fallback + hidden debug trace
```

## 设计亮点

### 先在可见图上 grounding，才读取隐藏状态

系统先基于 reviewed graph 识别 question 直接涉及的节点。无 grounding 或多独立问题时走 policy fallback，且不加载 hidden map；正常路径也仅加载直接 grounded nodes 的 state/evidence。这个顺序将“问题可解释性”和“隐藏信息最小访问”同时做成执行约束。

### Blueprint 是推理与自然语言之间的安全契约

Answer Policy 从隐藏状态和证据派生去标识化的结构化 `Simulator Answer
Blueprint`，描述 stance、answer shape、content unit 和 overclaim limits。
Generation 只接收 blueprint，不接收原始 map；这样自然表达与隐藏推理脱钩，
也让 policy schema 能在生成前拒绝隐藏字段和越权内容。

### 失败闭合

当前实现没有独立的 post-generation semantic validator。Policy 先校验
blueprint schema 与 forbidden fields；generation 失败、超时、为空或解析异常时
进行有限重试，随后返回 Safe Fallback。结构隔离减少原始隐藏字段直接进入生成器，
但语义 fidelity 与对抗性 leakage 仍需实验验证。

### 调试与可见 transcript 分开

每轮写入只对 benchmark author 可见的 debug trace，可含 grounding、blueprint
和 generator metadata。Tested Agent 只得到回答与粗粒度 observation；正式
transcript 也不得包含 trace id、grounded node id 或 hidden internals。

## 关键边界

- Profile Context 只可调整措辞，不得增加用户事实或能力主张。
- 可见对话用于承接追问，但不能更新 hidden static knowledge state。
- label-seeking 问题可以得到自然自述，绝不可得到 `L0`–`L5`、evidence id 或整张 state table。
- “没有直接暴露 raw hidden fields”是代码边界；“回答忠实且无语义泄漏”是由
  `experiments/02_simulator_human_validity/` 检验的研究假设。
