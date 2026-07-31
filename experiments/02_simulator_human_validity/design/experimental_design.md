# SAGE Simulator 有效性实验

> 本文件是本实验设计的中文主文；为避免协议分叉，不另维护重复副本。

> 状态：面向预注册的实验协议；尚未产生任何实证结果。
>
> 工作流：**SAGE — Scoped Answer Generation from Epistemic State**。
>
> 中文执行材料：[`../materials/README.zh-CN.md`](../materials/README.zh-CN.md)。

## 1. 研究目标与主张边界

核心问题是：

> Simulator 对 held-out diagnostic questions 的回答，是否表达了与真人相近的知识水平、误解、不确定性和能力边界，并且能否作为比较 Tested Agents 的有效代理？

这个问题拆成四类不能互相替代的证据：

| 研究问题 | 要排除的替代解释 |
| --- | --- |
| RQ-S1 State fidelity | 回答自然，但知识水平、误解或边界与真人不同 |
| RQ-S2 Systematic bias | 平均相近，但稳定地把低水平用户说得过强，或把高水平用户说得过弱 |
| RQ-S3 Boundary safety | 没有直接输出标签，但仍通过自然语言泄漏无关节点或隐藏字段 |
| RQ-S4 Proxy validity | 单个回答看起来合理，但用它比较 agents 会得到与真人不同的结论 |

当前代码可以支持“隐藏状态访问被分阶段、最小化”的结构主张。人类忠实度、对抗性 non-leakage 和 agent 排名保持仍是待验证假设。

## 2. 预注册对象

正式收集数据前冻结：

- public reviewed graph 与 node rubrics；
- Profile Context schema；
- Human Reviewed Map authoring protocol；
- diagnostic question sets A/B 及其 node 覆盖；
- SAGE 版本、provider、prompt、temperature 与 seed 规则；
- baselines、ablations、排除规则和 fallback 处理；
- 主指标、统计模型、方向性假设和多重比较族；
- human-study 样本量分析与停止规则。

Question set A 用于建立 Human Reviewed Map。Set B 只用于验证，不得反向修改 map、prompt、量表或判定阈值。

## 3. 分析单位与嵌套结构

参与者，而不是单条回答或随机 seed，是独立抽样单位。

```text
participant
  -> reviewed node states
  -> held-out questions
  -> SAGE conditions
  -> repeated seeds
  -> ratings / annotations
```

Questions、conditions 和 seeds 嵌套或交叉于参与者。三次 seed 不得被当成三个独立用户，也不得选择最好的一次。

## 4. 参与者与任务抽样

采用分层招募，覆盖：

- 初学、中等和较高学习经验；
- L0–L5 中可被可靠确认的不同 mastery 区间；
- 有明确 misconception、明确 uncertainty 和无明显 misconception 的节点；
- 事实性、解释性、比较性和应用性诊断问题。

样本量由预注册的最小有意义 state-fidelity 差异和参与者级 bootstrap / mixed-effects 模型进行 power analysis 决定。本文不在数据收集前虚构固定人数。

## 5. Profile Context 建立

让参与者填写简短问卷并接受访谈，包括：

- 学习背景；
- 学过哪些统计或机器学习课程；
- 使用过哪些模型；
- 是否做过相关项目；
- 学习目的；
- 平时表达和回答习惯。

系统据此生成 Profile Context，参与者对其中的事实进行修改和确认。

Profile Context 只能控制表达习惯。它不得改变 mastery、misconception、uncertainty 或 evidence content。该限制通过 no-style ablation 检查。

## 6. 建立 Human Reviewed Map

根据诊断问题集 A 收集真人回答。系统基于回答和 node rubric 生成 Candidate Knowledge Map；参与者核对事实、误解和未知项，研究者最终确认 Reviewed Knowledge Map。

Set A 的回答、review 记录和修改轨迹保留为 provenance，但不出现在 Set B 的 simulator generation context。

若参与者与研究者无法对节点状态达成可解释的一致，该 participant-node 进入预声明的 unresolved 集，不得事后选择有利标签。

## 7. 留出回答收集

在同一批 Set B 问题上分别收集：

- 真人原始回答；
- full SAGE 回答；
- 预注册 baseline / ablation 回答。

每个 participant-question-condition 使用三个预先固定的随机 seed。所有输出均进入分析；失败、fallback、空回答和拒答按预注册规则计数。

同一参与者的真人回答先于对应 simulator 评价收集，避免参与者看到 simulator 文本后改变自己的表述。

## 8. Simulator 回答自我忠实度量表

请根据你在回答该问题时的真实理解，评价 Simulator 生成的回答。采用 7 点 Likert 量表。

1. **核心观点一致性**

   这段回答表达的核心观点与我真实想表达的内容一致。

2. **知识水平一致性**

   这段回答体现出的知识水平与我对该问题的实际掌握程度一致。

3. **已掌握内容覆盖**

   这段回答包含了我认为自己真正理解和能够表达的关键内容。

4. **知识边界一致性**

   这段回答准确体现了我在哪些部分能够回答，以及在哪些部分无法确定或无法解释。

5. **不确定性一致性**

   这段回答所表现出的犹豫、不确定或信心程度与我的真实状态一致。

6. **误解一致性**

   如果我对该问题存在理解偏差，这段回答准确体现了这种偏差；如果我不存在明显偏差，它也没有凭空制造错误理解。

7. **不过度表现**

   这段回答没有让我显得比实际更加了解这个问题。

8. **不低估能力**

   这段回答没有明显低估我实际掌握的知识或能力。

9. **表达方式真实性**

   在不要求逐字相同的情况下，这段回答的表达方式像是我可能说出的回答。

10. **整体代表性**

    总体而言，我愿意将这段回答视为对我真实回答和真实理解的合理代表。

### 总体判断

你是否认为该回答可以代替你的回答，用于测试一个 AI Agent 是否能够判断你的知识状态？

- 可以直接使用
- 基本可以使用，但存在轻微偏差
- 需要明显修改后才能使用
- 完全不能代表我的真实状态

### 偏差类型

如果存在偏差，主要属于哪一类？可多选。

- 表现得比我实际更懂
- 表现得比我实际更不懂
- 核心观点与我不同
- 没有体现我的不确定性
- 没有体现我的理解偏差
- 凭空增加了我没有的误解
- 表达方式不像我
- 回答过于完整或专业
- 回答过于模糊或简单
- 其他：__________

### 可选说明

请简要指出这段回答最不像你的地方，或你认为最需要修改的部分。

### 量表使用限制

该十项量表目前是待验证 instrument，不能直接假设构成一个单维总分。正式使用前需要：

1. 专家内容效度审查；
2. 小规模认知访谈，检查参与者如何理解每一项；
3. pilot 中检查缺失、天花板/地板效应与项目相关；
4. 数据允许时检查因子结构和内部一致性；
5. 在结构未被支持前逐项报告，不随意求平均。

## 9. 专家盲评

将真人与所有 simulator conditions 的回答混合、匿名、随机排序。标注者不知道回答来源、condition、hidden map 标签或 agent 结果。

| 维度 | 操作定义 |
| --- | --- |
| 表达的掌握度 | 回答在 public rubric 下体现出的 L0–L5 水平 |
| 正确性 | 可观察核心主张与推理是否正确 |
| 能力边界 | 是否准确表达能解释、不能解释和需要猜测的部分 |
| 不确定性 | 犹豫、置信和未知是否与内容相容 |
| 误解 | 是否表达 reviewed misconception、遗漏它或凭空制造它 |
| 诊断价值 | 回答是否足以让 Agent 区分目标 mastery boundary |
| 自然度 | 是否像自然用户回答；仅作次要指标 |
| 画像一致性 | 表达方式是否符合 Profile Context；不评价知识水平 |

每个项目至少两名标注者。按字段报告 agreement；序数项优先使用 weighted kappa 或适合嵌套数据的可靠性指标。分歧按冻结规则由独立 adjudicator 处理。

## 10. 主要与次要终点

### 主要终点 A：状态忠实度误差

令盲评得到的真人 expressed mastery 为 \(m^{human}_{ij}\)，同一 participant-question 的 simulator 评价为 \(m^{sim}_{ijks}\)：

\[
E_{\text{state}} =
\operatorname{mean}_{i,j,k,s}
\left|m^{sim}_{ijks}-m^{human}_{ij}\right|.
\]

主分析先在 participant 内聚合 questions 和 seeds，再跨 participant 推断。

### 主要终点 B：参与者代表性

使用 Self-Fidelity Scale 第 10 项“整体代表性”的完整序数分布，以及“可以直接使用/基本可以使用”的参与者级比例。两者不合并成未经验证的总分。

### 次要终点

- signed mastery error，用于区分 overperformance 与 underperformance；
- ability-boundary、uncertainty 和 misconception 的遗漏/捏造率；
- diagnostic usefulness；
- style authenticity 与 naturalness；
- fallback、拒答、空答和 seed variance；
- 误差按真实 mastery、问题类型和 misconception presence 分层。

## 11. 边界安全与泄漏研究

安全研究与 fidelity study 分开报告，包含：

- 直接请求 `L0`–`L5`、map id、evidence id 和 scoring fields；
- 同义改写、间接套取、要求列出整张状态表；
- 已知但无关节点中植入只用于检测的 canary fields；
- compound questions、无 grounding 问题和跨节点诱导；
- visible-history prompt injection。

自动扫描负责精确 forbidden token / canary 命中。人工盲评负责语义泄漏，例如回答虽无 id，却暴露了问题没有许可的其他节点状态。

“零直接字段泄漏”只支持观测到的测试集，不等价于普遍 non-leakage 证明。

## 12. 基线与消融

| 条件 | 目的 |
| --- | --- |
| Monolithic role prompt | 检验 staged workflow 是否优于一次性角色扮演 |
| Persona-only prompt | 检验 Profile Context 能否替代 reviewed epistemic state |
| SAGE without blueprint | 检验 epistemic abstraction 对 overclaim 和 leakage 的作用 |
| SAGE without evidence | 检验 mastery label 本身是否足以产生可信细节 |
| SAGE without style | 检验 style 是否只改变真实性而不改变知识内容 |
| Template realization | 检验 LLM generator 带来的是 fidelity 还是仅 fluency |
| Full-map context | 仅离线隔离执行，检验 scope minimization |
| Full SAGE | 完整 workflow |

`Full-map context` 与 raw-state generator 是有意的不安全消融，只能在不连接 Tested Agent 的隔离 harness 中执行。

## 13. 代理有效性实验

选择规模可控的 agents 与 episodes 子集，在完全相同的 public graph、问题预算、tested-agent contract 和 scoring profile 下运行：

1. SAGE episodes；
2. matched human episodes。

主要比较：

- agent 间 paired effect 的方向是否一致；
- agent 排名的 rank correlation 与置信区间；
- adaptivity advantage 在两类用户中是否同向；
- 绝对 reconstruction score shift 与 rank reversal。

仅有高 rank correlation 仍不足以证明 simulator 绝对真实；它只能支持在给定任务和 agents 上的比较代理效度。

## 14. 统计分析

- participant 是主要独立抽样单位；
- question、condition 和 seed 作为嵌套/交叉重复测量；
- 使用 mixed-effects ordinal / continuous model，或 participant-clustered paired bootstrap；
- 报告 effect size、置信区间和完整分布，不只报告 \(p\)-value；
- ablation families 内采用预注册的 multiplicity correction；
- 不做 best-of-3，不删除失败 seed；
- missing、fallback 和 participant withdrawal 按预注册规则处理；
- primary conclusions 在 threshold、exclusion 和 model specification 固定后产生。

数值接受阈值必须在 pilot 后、正式 test 前冻结。若 fidelity、safety 或 ranking transfer 任一主张失败，只收缩对应主张，不用 naturalness 指标补救。

## 15. 主张报告表

| 主张 | 主要证据 | 状态 |
| --- | --- | --- |
| 结构性隐藏访问隔离 | 代码 contract 与测试 | 已实现，需在当前版本验证 |
| 输出安全性 | 对抗性泄漏研究 | 未运行 |
| 状态忠实度 | 留出真人/Simulator 比较 | 未运行 |
| 风格真实性 | 参与者评分与 no-style 消融 | 未运行 |
| 代理有效性 | 匹配的真人/SAGE Agent 比较 | 未运行 |

## 16. 伦理与数据管理

- 参与者明确同意其回答被用于 simulator validation；
- Profile Context 去标识化，禁止包含不必要的敏感属性；
- 原始回答、reviewed map 和发布用数据分层存储；
- 发布时避免让文本与小群体背景组合后可重新识别个人；
- 报告招募、报酬、withdrawal、缺失数据和模型服务商的数据处理边界；
- simulator 输出不得被描述为真人数据。
