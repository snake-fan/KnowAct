# 最终方法：SAGE User Simulator

[English](04_final_method.md)

> 状态：当前实现的最终汇总方法契约。
> SAGE 已实现；真人忠实度与代理有效性尚未得到验证。
> 最后更新：2026-08-01。

## 1. 方法定位

SAGE 全称为 **Scoped Answer Generation from Epistemic State**，中文为“基于认知状态的作用域受限回答生成”。它把一张 reviewed hidden Knowledge Map 转换为对单个诊断问题的自然、有限回答。

SAGE 是信息流方法，不是人类认知模型。它的核心贡献是分离公开 grounding、局部隐藏状态访问、回答内容推理和表层语言生成。

该方法需要支持知识状态诊断，同时避免把 Simulator 变成可查询的 benchmark oracle。Tested Agent 只能从可见回答推断用户状态，不能读取 hidden map。

本文汇总可执行方法。

文献质量审核见 [`02_reviewed_paper_pool.md`](02_reviewed_paper_pool.md)。证据综合与理论论证见 [`03_evidence_synthesis_and_sage.md`](03_evidence_synthesis_and_sage.md)。

## 2. 主张边界

本方法区分三类主张。

- **已实现事实：** 当前服务已实现分阶段访问、严格结构化中间对象、有限重试、safe fallback，以及可见与隐藏 artifact 分离。
- **文献支持的动机：** simulator、grounded dialogue、student modeling 和 plan-to-text 研究为这种分解提供设计依据。
- **研究假设：** SAGE 回答能够忠实代表真人，并保持对 Tested Agent 的比较结论；这需要真人实验验证。

“最终方法”表示本文是当前方法的规范汇总，不表示 SAGE 已通过真人有效性、对抗性泄漏或代理有效性检验。

## 3. 输入与不变量

一个 turn 绑定以下 artifact 和输入。

| 符号 | 输入 | 可见性与作用 |
| --- | --- | --- |
| \(\mathcal{G}\) | Reviewed Authored Knowledge Graph | 用于 grounding 的公开结构 |
| \(\mathcal{M}^{\star}\) | Reviewed hidden Knowledge Map | 仅 Simulator 可见的节点状态 |
| \(Z\) | Ground-Truth Evidence | 支撑 reviewed state 的隐藏证据 |
| \(q_t\) | 当前 Diagnostic Question | 可见 turn 输入 |
| \(\mathcal{H}^{vis}_{t-1}\) | Visible Dialogue Context | 可选的可见对话上下文 |
| \(\eta\) | Confirmed Profile Context style hint | 仅用于措辞风格 |

请求只选择 `benchmark_domain` 和 reviewed `map_id`。服务从不可变的 map manifest 推导 `graph_version` 和 `user_id`。

Candidate graph 和 candidate map 不能作为 Simulator 输入。缺失 Profile Context 不阻塞 turn；系统采用中性措辞，并记录不泄漏隐藏信息的 warning。

每个 turn 只包含一个普通诊断问题，或一个真正整合多个节点的 integrated question。多个相互独立的问题会得到 clarification，而不会被同时回答。

## 4. 端到端方法

```text
reviewed graph + diagnostic question + visible dialogue
  -> public-scope question grounding
  -> direct-node hidden context retrieval
  -> structured Simulator Answer Blueprint
  -> natural-language surface realization
  -> visible answer or safe fallback
  -> hidden audit trace
```

形式化表示为：

\[
S_t = g(q_t,\mathcal{G},\mathcal{H}^{vis}_{t-1}),
\]

\[
C_t = R(\mathcal{M}^{\star},Z;S_t),
\]

\[
B_t = \pi(C_t,q_t),
\]

\[
a_t \sim p_{\phi}(\cdot\mid B_t,\mathcal{H}^{vis}_{t-1},\eta).
\]

其中，\(S_t\) 是公开 grounding scope，\(C_t\) 是允许访问的局部隐藏上下文，\(B_t\) 是去标识化 blueprint，\(a_t\) 是可见回答。

执行顺序是方法的核心控制：确定作用域时看不到 hidden state；生成自然语言时看不到 raw hidden state。

## 5. 阶段一：公开作用域 Question Grounding

Grounder 先在 reviewed public graph 上解释问题，此时尚未加载任何 hidden map 数据。

结构化 grounding 结果包含：

- 直接 grounded node ids；
- integrated-question 标记；
- multiple-question 标记；
- label-seeking 标记；
- 未返回节点时的隐式 no-grounding 状态。

Provider-backed grounder 只接收可见节点 identity、name 和 definition。为解析追问指代，它最多接收上一轮可见对话。

它不能接收 mastery、misconceptions、unknowns、simulator-only evidence、graph edges、scoring 数据或完整 hidden map。

出现未知节点、provider 失败、timeout、非法 JSON 或 schema 错误时，系统回退到 rule-based grounding。模型给出的合法 no-grounding 结果不会被规则匹配覆盖。

这一阶段只决定作用域和标记，不决定用户掌握什么，也不决定回答的最终表达。

## 6. 阶段二：最小隐藏上下文检索

Grounding 成功后，context builder 只检索直接 grounded nodes 的状态。

每个 grounded node 加载：

- 可见的 node rubric 与 simulator behavior；
- reviewed `UserKnowledgeState`；
- 该 state 引用、可见性为 `simulator_only` 且 `node_id` 匹配的 evidence。

Graph neighbor 不会扩大隐藏上下文；edge 也不能授权访问额外节点状态。

如果 no-grounding，或问题包含多个独立问题，服务构建空 context，并且不加载 reviewed map 参与回答内容生成。

Visible dialogue 只用于承接追问措辞。它不会更新静态 hidden Knowledge Map，也不会变成隐藏的长期记忆。

## 7. 阶段三：Epistemic Answer Policy

Answer Policy 是推理边界。它把局部 reviewed state 转换为严格、去标识化的 `Simulator Answer Blueprint`。

Runtime 根据 grounding 固定 response mode：

| Grounding 条件 | Response mode |
| --- | --- |
| 多个独立问题 | `clarification` |
| 没有 grounded node | `non_answer` |
| 请求 hidden label 或 state table | `label_refusal` |
| 合法 grounded question | `answer` |

Rule-based fallback 把局部状态映射为五种 stance：正确理解、部分理解、不确定、不知道或误解。

低 mastery 且有明确 misconception 时使用 misconception；L4–L5 为 correct；L2–L3 为 partial；L1 或存在 unresolved unknown 时为 uncertain；其余情况为 not knowing。

Blueprint 包含：

- runtime 固定的 question text 与 response mode；
- primary stance；
- 第一人称 answer shape 与句子预算；
- answer strategy；
- 每个 grounded node 的 content unit；
- 有依据的 claim、boundary、misconception、uncertainty、cue 和 overclaim limit。

Blueprint 不包含 mastery label、node id、evidence ref、map id、user id、ground-truth label 或 scoring field。

LLM-backed policy 可以选择、压缩或改写 grounded rubric 与 evidence。输出必须通过严格 schema，并保持预期 node 顺序与 response mode。

出现不安全字段、未知节点、错误 integration mode、非法输出、timeout 或 provider 失败时，系统回退到 deterministic rule-based policy。

隐藏的 `Simulator Policy Decision Trace` 可以保留 mastery 和 evidence ref 供 benchmark author 审计，但它不会进入 generator，也不会暴露给 Tested Agent。

## 8. 阶段四：表层回答生成

Generator 只接收 blueprint、visible dialogue、可选 style hint 和 retry guidance。它不接收 raw graph、map、mastery label、evidence id 或完整 Profile Context。

Generator 生成一个简洁的第一人称回答。Integrated question 应生成一个整合回答，不能简单拼接多个独立回答。

Profile Context 只能在内容确定后调整语气、长度或措辞。它不能添加 blueprint 中没有的事实、经历、例子或能力。

模型输出必须是一个含非空 `answer` 的 JSON object。服务最多执行两次生成尝试。

Provider 失败、timeout、非法 JSON 或空回答会触发重试。尝试耗尽后返回固定 safe response：“I am not confident I can answer that cleanly right now.”

当前方法没有独立的生成后语义验证器。解析成功只能证明接口格式有效，不能证明语义忠实或在对抗场景下不泄漏。

## 9. 可见输出与隐藏审计

Formal turn response 只暴露：

- 自然语言回答；
- `answer`、`clarification` 或 `non_answer` 三类粗粒度 observation；
- 不泄漏隐藏信息的配置 warning；
- 可选 debug-trace reference 与 availability flag。

仅供 workbench 使用的 `turn-test` route 可以额外返回 directly grounded node ids，用于高亮 map。Formal episode transcript 不包含这些 id。

每个 turn 都会写入仅 benchmark author 可见的 debug trace。它可以记录 artifact binding、grounding decision、局部隐藏状态摘要、blueprint、model/parser artifact、尝试次数和 fallback 原因。

Visible transcript 不包含 hidden trace、blueprint、mastery、evidence ref、Profile Context、scoring state 或 raw model output。

## 10. Runtime 边界

`POST /api/simulator/turn` 是无状态的 Phase 5 检查边界。它可以接收请求携带的 visible dialogue，但不会建立服务端会话，也不会创建 Evaluation Episode。

Formal evaluation 使用 Episode Runtime。同一个 Simulator answer 在其中成为 Tested-Agent-visible `Interaction Observation`；hidden state 与 debug artifact 仍位于可见性边界之外。

Experiment 02 是独立的 participant-facing orchestration。它复用 SAGE 与 reviewed artifact，但不是 Episode Runtime，不调用 Tested Agent，也不执行 scoring。

## 11. 真人有效性协议

当前已实现的参与者路径保持窄而可执行：

```text
participant Profile revision and confirmation
  -> node-by-node Knowledge Map revision and confirmation
  -> sample 20 unique items from a versioned bilingual bank
  -> save the participant answer
  -> generate the SAGE answer to the same item
  -> collect five 1-5 self-ratings
  -> persist a resumable private session
  -> retain answer pairs for later blind review
```

真人回答必须先保存，才能生成或展示 Simulator 回答。20 道题彼此独立，前一题的对话不会进入下一题。

五项评分覆盖核心内容、表现出的知识水平、能力边界、表达方式和整体代表性。完成的问答对保持 `blind_review_status = pending`，供后续专家盲评。

这一协议建立了数据收集路径，不构成实验结果。伦理审查、领域专家题目审核、双语等价性审核、认知访谈、pilot 与冻结分析计划仍是正式收集门槛。

## 12. 评价逻辑

SAGE 必须分层评价。

| 层级 | 核心问题 | 所需证据 |
| --- | --- | --- |
| 结构访问 | 每个组件是否只接收获授权字段？ | 代码审核、契约、测试、canary |
| 输出安全 | 回答是否避免直接和语义泄漏？ | 对抗性 leakage suite 与盲评 |
| 状态忠实 | 回答是否表达预期 mastery 与 boundary？ | 匹配真人回答与状态评分 |
| 个人忠实 | 参与者是否认为回答能代表本人？ | 参与者自评与评论 |
| 代理有效 | Simulator 是否保持 agent effect？ | 匹配的真人/Simulator agent 比较 |

自然度是次要指标。流畅回答仍可能泄漏 hidden state、夸大能力、抹去 misconception，或改变 agent 排名。

## 13. Baseline 与 Ablation

完整验证设计应比较：

- monolithic role prompt；
- persona-only prompt；
- 去掉 blueprint 的 SAGE；
- 去掉 reviewed evidence 的 SAGE；
- 去掉 style context 的 SAGE；
- 使用 rule-based realization 的 SAGE；
- 隔离环境中的 full-map-context safety ablation；
- full SAGE。

Full-map 和 raw-state 条件不适合常规 benchmark execution。它们只能在隔离的 validation harness 中运行，且输出不能展示给 Tested Agent。

主要假设包括：更低泄漏、更少 mastery 高估、更好保留不确定性与误解、style 不引起内容漂移，以及与真人 agent 比较结论一致。

这些假设可以相互独立地失败。单一自然度或个人一致性分数不能验证整个方法。

## 14. 实现映射

| 方法组件 | 当前实现 |
| --- | --- |
| Grounding | `backend/knowact/simulator/grounding.py` |
| 局部隐藏上下文 | `backend/knowact/simulator/context_builder.py` |
| Answer policy 与 blueprint | `backend/knowact/simulator/policy.py` |
| 表层生成 | `backend/knowact/simulator/generators.py` |
| Retry 与 fallback | `backend/knowact/simulator/service.py`、`fallbacks.py` |
| Prompt contracts | `backend/knowact/simulator/templates/` |
| Hidden trace | `backend/knowact/simulator/debug_trace.py` |
| Single-turn API contract | `backend/knowact/simulator/turn.py`、`api/simulator.py` |
| 参与者验证 | `backend/knowact/runtime/simulator_experiment.py` |

实现细节的规范文档仍是 [`../../UserSimulator.md`](../../UserSimulator.md)。

参与者协议的规范文档仍是 [`../../../experiments/02_simulator_human_validity/design/experimental_design.md`](../../../experiments/02_simulator_human_validity/design/experimental_design.md)。

## 15. 当前局限与验证优先级

当前实现存在明确局限。

- 结构隔离无法阻止所有改写式泄漏或没有依据的语义暗示。
- Grounding 可能缩小或扩大问题作用域；rule fallback 主要依赖词汇匹配，当前也没有 grounding-confidence contract。
- Reviewed Knowledge Map 在 turn sequence 中保持静态；SAGE 不建模学习、疲劳、记忆变化或 state drift。
- 当前 style hint 较粗，尚未证明能够保留个人表达方式。
- 固定 safe fallback 是英文，可能降低中文实验中的自然度。
- 五项参与者评分尚未完成认知访谈与测量学验证。
- 当前没有真人数据支持 state fidelity、personal fidelity 或 proxy validity 主张。

验证应按以下顺序推进：

1. 对抗性 leakage probe 与 hidden-field canary；
2. held-out 真人问答对及盲法 state/boundary 评分；
3. blueprint、evidence、style 与 generator ablation；
4. 匹配真人/Simulator 条件下的 agent effect direction 与 ranking 比较。

## 16. 最终方法陈述

SAGE 首先确定诊断问题在公开图谱上的作用域。

随后只检索被直接授权的 hidden state，把该状态抽象为去标识化 answer blueprint，最后把 blueprint 实现为可见回答。

当前最强主张是结构性的：分阶段契约与失败闭合减少了 raw hidden state 的直接暴露。

真人忠实度、语义不泄漏和代理有效性仍是可证伪的经验主张。只有完成对应层级的验证后，才能报告这些结论。
