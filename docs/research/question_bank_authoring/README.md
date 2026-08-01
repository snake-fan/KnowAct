# Atomic Bilingual Question-Bank Authoring

## 1. 目标与产物

本轮把 Experiment 02 题库从单一 ISLP、21 道复合提问重构为三个独立 v2 题库：

| Domain | Questions | Candidate-aligned concepts | English–Chinese pairs |
| --- | ---: | ---: | ---: |
| Economy | 80 | 22 | 80 |
| ISLP | 80 | 21 | 80 |
| OSTEP | 80 | 24 | 80 |

每题只诊断一个认知操作。题库保存可呈现给参与者的题面；`reviews/` 保存 authoring-only
来源审核、角色试答、认知信号和内容哈希。试答答案不进入参与者 API，也不进入
tested-agent visible context。

## 2. 来源质量审核

只接受教材作者或教材项目维护的第一方材料。网络题目用于确认概念覆盖、题型和迁移
场景，不直接复制；最终题面均为面向当前 concept catalog 的原创中英文改写。

| Domain | Source | Authority and use | Accepted transfer boundary |
| --- | --- | --- | --- |
| Economy | [CORE Econ, Unit 1](https://books.core-econ.org/the-economy-v1/book/text/01.html), [Unit 2](https://books.core-econ.org/the-economy-v1/book/text/02.html), [Unit 3](https://books.core-econ.org/the-economy-v1/book/text/03.html), [Unit 4](https://books.core-econ.org/the-economy-v1/book/text/04.html) | CORE 官方开放教材；用于审核 capitalism、growth、choice 与 social interaction 的概念边界和练习风格 | 只迁移概念与推理形式，不复制练习；短题不能替代完整历史、图形或博弈推导 |
| ISLP | [official book site](https://www.statlearning.com/), [official courses](https://www.statlearning.com/online-courses), [Python companion](https://intro-stat-learning.github.io/ISLP/) | 作者维护的教材、课程和 Python companion；用于审核 Chapters 2–3 范围、术语及应用层级 | 不把 API 示例当作测量证据；短答题不覆盖完整建模流程 |
| OSTEP | [official book site](https://pages.cs.wisc.edu/~remzi/OSTEP/), [process API chapter](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-api.pdf), [limited direct execution chapter](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-mechanisms.pdf), [official homework catalog](https://pages.cs.wisc.edu/~remzi/OSTEP/Homework/homework.html), [homework repository](https://github.com/remzi-arpacidusseau/ostep-homework) | 作者维护的教材、章节和 simulator homework；用于审核 process、control transfer 与 scheduling 场景 | JSON 题目不复刻 simulator trace；架构细节被抽象化，仍需系统领域专家复核 |

每个具体题目通过 `source_reference_ids` 指向审核文件中的来源记录；来源记录同时保存
authority、relevance、evidence used 与 transfer limits。只有 `decision = accepted` 的来源
可以被题目引用。

## 3. 单题审核流程

题目只有依次通过以下 gate 才写入正式 v2 JSON：

1. **Concept gate**：只针对一个 candidate-aligned `target_concept`。
2. **Atomicity gate**：只声明一个 `cognitive_operation`；每种语言只有一个终止问号，
   不使用“解释并比较”“判断并说明”等复合任务。
3. **Boundedness gate**：英文不超过 55 词/320 字符，中文不超过 180 字符。
4. **Bilingual gate**：中英文保持相同场景、条件和认知操作。
5. **Roleplay gate**：轮换五种与领域相符的学习者/初级从业者角色进行试答。
6. **Brevity gate**：试答必须在 45 个英文词以内；当前实际范围为 3–23 词。
7. **Cognitive-signal gate**：试答必须足以暴露预期 L2、L3 或 L4 信号，而不靠第二问补充诊断。
8. **Integrity gate**：审核文件覆盖且仅覆盖全部题目，并绑定题库文件 SHA-256。

`identify` 对应 L2；`explain`、`predict`、`calculate`、`choose`、`interpret` 对应 L3；
`compare`、`diagnose`、`evaluate` 对应 L4。这是 authoring screening 的预期信号标签，
不是经过 item-response 或认知诊断模型校准得到的难度参数。

## 4. 接受结果

240 道题均通过本轮 machine-enforced atomicity/boundedness 检查和 author-side 角色试答：

- Economy：80/80 accepted，五种角色，四项第一方来源；
- ISLP：80/80 accepted，五种角色，四项第一方来源；
- OSTEP：80/80 accepted，五种角色，六项第一方来源。

每个题库仍只从 80 道中按持久化 seed 抽取 20 道不重复题用于一次参与者会话。扩容用于
覆盖和抽样，不改变一次会话的负担。

## 5. 尚未完成的验证

本轮 screening 能排除明显复合提问、过长题面、缺失来源、缺失试答和审核文件漂移，
但不能证明题库已经是正式量表。正式收集前仍需：

- Economy、ISLP、OSTEP 各自的领域专家审核内容正确性和概念覆盖；
- 双语专家审核语义等价，并通过参与者认知访谈检查理解偏差；
- reviewed graph 发布后填写 `reviewed_target_node_ids`，当前不得绑定 candidate node；
- pilot 后估计题目难度、区分度、重复度与抽样条件间可比性；
- 冻结题库版本、source snapshot、graph version 与排除规则。

因此当前三个题库适合开发与 pilot，`expert_review_status` 明确保持 `pending`，不能据此
声称已建立内容效度或心理测量效度。
