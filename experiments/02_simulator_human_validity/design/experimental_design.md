# SAGE Simulator 个人一致性实验

> 状态：简化后的可执行主协议。当前实现支持端到端数据收集；尚未产生真人实验结果。
>
> 当前研究对象：参与者本人对其回答与 SAGE Simulator 回答的一致性判断。
>
> 后续扩展：独立专家盲评。泄漏挑战、复杂消融和 Tested-Agent 排名迁移不进入当前参与者主流程。

## 1. 研究问题

参与者在确认自己的 Profile Context 和 Knowledge Map 后，SAGE Simulator
针对同一组诊断问题生成的回答，能否代表参与者的：

- 核心回答内容；
- 表现出的知识水平；
- 能力与不确定性边界；
- 表达方式；
- 整体回答倾向。

本实验先收集参与者自评。专家盲评使用已保存的问答对，在后续独立阶段执行。

## 2. 自动化主流程

```text
匿名参与者编号
  -> 输入个人背景、经历、目标与回答偏好
  -> 生成 Profile Context
  -> 参与者修订并确认
  -> 基于 reviewed graph 生成 Candidate Knowledge Map
  -> 参与者逐节点修订 mastery / misconception / unknown boundary
  -> 确认不可变的 participant-reviewed map
  -> 从独立双语题库按固定 seed 抽取 20 道不重复问题
  -> 每题先保存真人回答
  -> SAGE 对同一问题生成回答
  -> 参与者对照两份回答完成自评
  -> 20 题完成后保存实验会话
  -> 问答对进入待盲评状态
```

参与者会话通过独立部署的 `simulator-test-frontend/` 完成，不进入内部 research
workbench。中途退出后，可以使用浏览器保存或本人持有的恢复码继续。

## 3. Profile Context

参与者输入应包括相关学习背景、学过或使用过的方法、实践经历、学习目标，以及回答长度、
解释形式和面对不确定性时的表达偏好。

系统生成结构化 `Profile Context` 后，参与者可以修订
`summary`、`background`、`prior_experience`、`goals` 和 `preferences`。
确认后的 snapshot 不再覆盖；进一步修改需要新的匿名用户 ID。

Profile Context 只提供人物背景与表达风格依据。节点级知识状态由 Knowledge Map
表达。

## 4. Participant-Reviewed Knowledge Map

系统使用 confirmed Profile Context 和 reviewed graph 生成 Candidate Knowledge
Map。参与者逐节点检查并修订：

- `mastery_level`；
- `misconceptions`；
- `unknowns`；
- 可选个人修订说明。

参与者确认后，系统按照 reviewed graph 顺序生成不可变的 ground-truth map，并为每个
节点建立 `simulator_only` 的 `self_report` evidence。L2-L3 节点至少保留两条
evidence，其余节点至少一条。

原始候选状态、参与者修订和最终 map 分开保存，以保留 provenance。参与者确认后的
map 才能进入 Simulator Test Session。

## 5. 独立双语题库

题库是独立版本化材料，不嵌入前端代码或实验会话：

```text
benchmark/question_banks/{bank_name}.json
```

每道题包含稳定 `question_id`、`target_concept`、`question_type`、单一
`cognitive_operation`、来源引用、英文题面、中文题面和可选 reviewed graph node
binding。英文和中文各只能有一个终止问号，避免通过“解释并比较”等复合提问无限扩张
单题诊断负担。

当前为 Economy、ISLP、OSTEP 各提供 80 道中英文配对题。每个参与者从所选 domain
题库按持久化 `sampling_seed` 抽取 20 道不重复问题。语言只改变题面，不改变问题身份。
每套题库必须有第一方来源审核与逐题角色试答审核；试答需简短并暴露预期 L2–L4 认知
信号，审核文件以 SHA-256 绑定题库原文。试答属于 authoring-only artifact，不向参与者
或被测 agent 展示。

正式收集前仍应由领域专家检查题目内容、双语等价性和与当前 reviewed graph 的概念覆盖，并补齐
`reviewed_target_node_ids`。未绑定 node id 不阻塞开发和 pilot，但不得被描述为完成
正式量表验证。

## 6. 同步回答边界

每道题按以下顺序处理：

1. 前端只显示题目；
2. 参与者提交自己的回答；
3. 后端立即保存真人回答；
4. 后端使用同一 `question_id` 和题面调用 SAGE；
5. Simulator 回答、observation、warning 和隐藏 debug-trace 引用写入私有会话；
6. 前端并排展示真人回答和 Simulator 回答；
7. 参与者完成自评。

Simulator 在真人答案提交前不得生成或展示对应回答，避免参与者受 Simulator 文本影响。
20 道题彼此独立，不把前一题对话作为下一题的 visible dialogue context。

## 7. 参与者自评

每个问答对使用五个 1-5 分条目：

1. 核心内容一致性；
2. 知识水平一致性；
3. 能力边界一致性；
4. 表达方式一致性；
5. 整体代表性。

另外收集：

- `direct_use`：可以直接替代本人回答；
- `minor_bias`：基本可以，但有轻微偏差；
- `major_revision`：需要明显修改；
- `not_representative`：不能代表本人；
- 可选自由文本说明。

当前五项是简化的研究 instrument。正式确证性分析前仍需认知访谈和 pilot。未经验证
前，应逐项报告和报告完整分布，不应默认取一个总平均分。

## 8. 数据与断点恢复

每个实验会话保存 participant code、confirmed profile/graph/map identity、question-bank
identity/version、语言、provider、sampling seed、20 道抽样题及顺序、两类回答、自评、
completion 状态和 `blind_review_status = pending`。

原始会话写入：

```text
experiments/02_simulator_human_validity/results/private/sessions/{session_id}/session.json
```

参与者 Map 修订轨迹写入：

```text
experiments/02_simulator_human_validity/results/private/map_reviews/{map_id}.json
```

两个目录均被 Git 忽略。会话采用原子文件替换保存，每题完成后即可断点恢复。

## 9. 当前分析

第一阶段只回答个人一致性问题，报告：

- 每个条目的完整 1-5 分布；
- 每位参与者和每道题的分布；
- `direct_use + minor_bias` 比例；
- Simulator failure、fallback 和 warning 比例；
- 按 mastery、question type 和语言的描述性分层；
- 参与者自由文本中反复出现的偏差类型。

参与者是主要抽样单位，20 个回答不能当作 20 个独立参与者。

## 10. 后续专家盲评

完成参与者自评后，再从已保存问答对生成独立盲评包。专家不知道回答来源、
participant code、hidden map、participant self-evaluation 或 debug trace。

盲评可以评价正确性、表达掌握度、能力边界、误解和自然度。盲评结果必须保存为独立
artifact，不能覆盖原始 participant session。

## 11. 当前不进入主流程的研究

以下内容有价值，但不阻塞当前可执行主流程：

- 对抗性 leakage challenge suite；
- 多 seed、八条件 baseline/ablation；
- matched human episodes；
- Tested-Agent 排名相关、效应方向与 rank reversal。

它们应在获得第一批问答对、确认核心收集流程可用后，作为独立研究模块逐步加入，不能
再要求普通参与者完成额外人工步骤。

## 12. 伦理与主张边界

- 使用匿名 participant code，不在实验系统中存储姓名和联系方式；
- Profile Context 不收集不必要的敏感属性；
- 原始回答、Profile Context、Knowledge Map 和自评属于受限数据；
- 外部模型 provider 的数据处理边界必须写入知情同意材料；
- Simulator 输出不能标记为真人数据；
- 在真实参与者数据收集和分析完成前，只能声称自动化流程已实现，不能声称 SAGE
  已获得真人有效性支持。
