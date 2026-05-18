# Knowledge Graph

## Knowledge Node

### Node 设计原则

Node 设计原则：

``` text
1. 用户可以用 1-2 个问题暴露是否掌握  
2. 它和其他节点有明确依赖关系  
3. 它不是一个完整领域，也不是一个太小的术语  
4. 它能被定义、举例、应用、比较
```

可以参考 `ZettelKasten 笔记法`

参考：

``` JSON
{
  "id": "epistemic_uncertainty",
  "name": "Epistemic Uncertainty",
  "type": "concept",
  "definition": "Uncertainty caused by lack of knowledge or limited data.",
  "diagnostic_goal": "User can distinguish model uncertainty from data noise and explain why more data can reduce it.",
  "source": ["textbook_chapter_3", "survey_section_2.1"]
}
```

#### 1）可解释

用户应该能说清楚它是什么。

例如：

``` text
epistemic uncertainty
```

不是只知道名字，而是能解释：

``` text
模型因为缺少知识或数据而产生的不确定性。
```

---

#### 2）可诊断

你能为它设计一个问题，判断用户是否掌握。
比如：

``` text
为什么 epistemic uncertainty 可以通过增加数据减少？
```

如果一个 node 没法被问出来，它就不适合做主动探索节点。

---

#### 3）粒度适中

不要太大

``` text
Machine LearningActive LearningLLM Alignment
```

这些太大，一问问不清。
也不要太小：

``` text
符号 σ公式里的某个下标一句定义里的某个词
```

这些太碎，会让图爆炸。

比较好的粒度是：

``` text
acquisition functionepistemic uncertaintyaleatoric uncertaintyexpected information gainposterior predictive distributionpreference model ensembleadapter ensemblediversity sampling
```

判断标准是：

> 一个 node 最好能用 1-3 个诊断问题判断掌握程度。

---

#### 4）稳定

node 不应该依赖某篇论文的表述方式，而应该是领域里相对稳定的知识单位。
比如：

``` text
BALDexpected information gainuncertainty samplingknowledge tracingprerequisite relation
```

比某篇论文里临时命名的模块更适合作为 node。

---

#### 5）有证据来源

每个 node 最好能追溯到：

``` text
教材章节课程 slidesurvey paper经典论文术语表领域专家确认
```

---

### Knowledge Node v1 Design

本节记录 KnowAct v1 中 `Knowledge Node` 的结构约定。

#### 概念边界

`Knowledge Node` 是用户无关的知识单位。它描述一个稳定、可诊断、可追溯来源的概念，以及该概念在不同掌握等级下应如何被诊断和模拟。

`MasteryScale` 是全局统一的 L0-L5 掌握程度量表。它提供每个等级的固定名称和划分依据，用于保证不同 node 之间的可比性。

`User Knowledge State` 是用户相关状态。它引用一个 `Knowledge Node`，并记录某个用户在该 node 上的当前 `mastery_level`、置信度、证据、误解和未知项。用户状态不应直接写进 `Knowledge Node`。

`Evidence` 是可追溯观察或画像依据。它可以用于支持用户模拟，也可以用于支持被测 agent 的实时推断，但两者的可见性和生命周期不同。

``` text
Knowledge Node
= 概念本体 + 针对该概念的 L0-L5 诊断 rubric

MasteryScale
= 全局固定的 L0-L5 等级定义

User Knowledge State
= 某个用户在某个 node 上的当前状态

Evidence
= 支撑状态判断或模拟回答的可追溯依据
```

#### MasteryScale

`MasteryScale` 是全局规范。每个等级的 key 和名称固定，node 不能覆盖这些 label，只能在 `levels` 中描述该概念在对应等级下的具体表现。

| 等级 | 名称 | 划分依据 | 可观测表现 |
| --- | --- | --- | --- |
| L0 | 无有效理解 / 错误识别 | 用户不能识别该概念，或把它和无关概念混淆 | 听过词但说不清；定义明显错误；答非所问 |
| L1 | 术语识别 / 记忆 | 具备 factual recall | 能复述定义、关键词、公式，但解释依赖背诵 |
| L2 | 基本解释 | 能用自己的话解释核心含义 | 能给例子，但例子单一；边界条件不清 |
| L3 | 结构化理解 | 能把该 concept 与相关概念、前置概念、反例联系起来 | 能比较 A/B；能说明适用条件；能指出常见误区 |
| L4 | 应用与迁移 | 能在新问题中使用该概念 | 能解决变体问题；能判断什么时候该用/不该用 |
| L5 | 反思性 / 生成性理解 | 能批判、抽象、教学、生成新问题 | 能解释为什么；能设计例子、类比、反例；能发现模型/论文中的隐含假设 |

设计原则：

``` text
1. L0-L5 是全局统一量表，不随 node 改名。
2. Knowledge Node 的 levels 是对全局量表的 node-specific 具体化。
3. User Knowledge State 使用 "L0" 到 "L5" 字符串引用等级。
4. 正式 benchmark node 必须完整覆盖 L0-L5。
```

#### Knowledge Node 最小字段

v1 中，`Knowledge Node` 的最小字段为：

``` json
{
  "id": "epistemic_uncertainty",
  "name": "Epistemic Uncertainty",
  "type": "concept",
  "definition": "Uncertainty caused by lack of knowledge or limited data.",
  "diagnostic_goal": "Assess whether the user can distinguish reducible model uncertainty from irreducible data noise.",
  "levels": {},
  "source": ["textbook_chapter_3", "survey_section_2.1"]
}
```

字段含义：

- `id`：稳定的机器可读标识。
- `name`：人类可读名称。
- `type`：v1 暂时只使用 `"concept"`，不扩展复杂 taxonomy。
- `definition`：概念定义。
- `diagnostic_goal`：该 node 的总体诊断目标，即这个概念整体要测什么。
- `levels`：固定包含 `L0` 到 `L5` 的对象。
- `source`：知识点来源，用于证明该 node 是可追溯的知识单位。

`source` 只挂在 node 顶层。level 不单独维护 `source`，因为 source 证明的是知识点本身可查，而不是每个掌握程度 rubric 的出处。

#### Levels 字段结构

`levels` 使用固定 key 对象，而不是数组：

``` json
{
  "levels": {
    "L0": {},
    "L1": {},
    "L2": {},
    "L3": {},
    "L4": {},
    "L5": {}
  }
}
```

每个 level 的结构为：

``` json
{
  "description": "For this node, what this mastery level concretely looks like.",
  "diagnostic_goal": "What should be checked to identify this level.",
  "positive_signals": [
    "Signals that support assigning this level."
  ],
  "negative_signals": [
    "Signals that reveal limits of this level or rule out higher levels."
  ],
  "misconception_signals": [
    "Characteristic misunderstandings that may appear at this level."
  ],
  "simulator_behavior": [
    "Knowledge-related behavior the user simulator should follow at this level."
  ]
}
```

正式 benchmark node 的校验规则：

``` text
每个 L0-L5:
- description: required, non-empty
- diagnostic_goal: required, non-empty
- positive_signals: required, non-empty
- simulator_behavior: required, non-empty
- negative_signals: required, may be empty
- misconception_signals: required, may be empty
```

`description` 是 node-specific 的等级描述。全局划分依据保留在 `MasteryScale` 中，不在每个 node 里重复写。

`positive_signals` 用于确认该等级。

`negative_signals` 用于描述该等级的限制，或排除更高等级。

`misconception_signals` 可以出现在所有等级。误解不等同于低等级；高等级用户也可能保留局部、边界性的误解。

`simulator_behavior` 只描述知识状态导致的回答行为，不包含用户人格、语气、偏好或学习目标。这些应属于用户画像或其他用户状态对象。

#### 不进入 Knowledge Node v1 的字段

以下内容暂不进入 `Knowledge Node` v1 schema：

- `status`：设计过程中的 draft / candidate / validated 状态通过目录或文件组织区分，不写进最终 node 数据。
- `boundary_diagnostics`：先只保留 `levels`，以后如果 L2/L3 这类边界判断变困难，再新增专门结构。
- level-level `source`：source 只用于 node 顶层。
- persona / preference：不放入 `simulator_behavior`。
- `difficulty`、`importance`、`tags`、`aliases`、`estimated_probe_count`、`owner`、`version`：v1 暂不加入，避免 schema 过早膨胀。

#### 示例

``` json
{
  "id": "epistemic_uncertainty",
  "name": "Epistemic Uncertainty",
  "type": "concept",
  "definition": "Uncertainty caused by lack of knowledge, limited data, or incomplete model understanding.",
  "diagnostic_goal": "Assess whether the user can distinguish reducible model uncertainty from irreducible data noise and use that distinction in reasoning about model behavior.",
  "levels": {
    "L0": {
      "description": "The user cannot identify epistemic uncertainty as a meaningful concept, or confuses it with unrelated ideas.",
      "diagnostic_goal": "Check whether the user recognizes the concept at all.",
      "positive_signals": [
        "Admits they do not know the term",
        "Gives an unrelated or incoherent definition"
      ],
      "negative_signals": [
        "Cannot connect the term to uncertainty, data, knowledge, or models"
      ],
      "misconception_signals": [
        "Treats epistemic uncertainty as user confidence or emotional uncertainty"
      ],
      "simulator_behavior": [
        "Responds with guessing or confusion",
        "May recognize the word uncertainty but cannot explain the epistemic part"
      ]
    },
    "L1": {
      "description": "The user can recall a memorized definition or keywords, but cannot explain the concept in their own words.",
      "diagnostic_goal": "Check whether the user only recognizes terminology or can explain beyond recall.",
      "positive_signals": [
        "Mentions lack of knowledge or limited data",
        "Repeats a textbook-like definition"
      ],
      "negative_signals": [
        "Cannot give a concrete example",
        "Cannot explain why more data may reduce this uncertainty"
      ],
      "misconception_signals": [
        "Equates all uncertainty with randomness"
      ],
      "simulator_behavior": [
        "Uses memorized phrasing",
        "Sounds correct at first but becomes vague when asked for examples"
      ]
    },
    "L2": {
      "description": "The user can explain epistemic uncertainty as uncertainty from limited knowledge or insufficient data, but handles only simple examples and unclear boundaries.",
      "diagnostic_goal": "Check whether the user can explain the core meaning in their own words.",
      "positive_signals": [
        "Explains that uncertainty can decrease when more relevant data is available",
        "Provides one simple example involving insufficient data"
      ],
      "negative_signals": [
        "Cannot clearly separate epistemic uncertainty from aleatoric uncertainty",
        "Struggles with cases where more data would not help"
      ],
      "misconception_signals": [
        "Treats noisy observations and missing knowledge as the same thing"
      ],
      "simulator_behavior": [
        "Answers with partial confidence and simple examples",
        "Avoids precise boundary cases unless prompted"
      ]
    },
    "L3": {
      "description": "The user can relate epistemic uncertainty to neighboring concepts such as aleatoric uncertainty, model uncertainty, data coverage, and reducibility.",
      "diagnostic_goal": "Check whether the user can reason about relationships, contrasts, and boundary cases.",
      "positive_signals": [
        "Compares epistemic uncertainty with aleatoric uncertainty",
        "Explains when more data should or should not reduce uncertainty",
        "Identifies common confusion between model uncertainty and data noise"
      ],
      "negative_signals": [
        "Needs familiar examples to maintain the distinction",
        "Cannot reliably transfer the distinction to a new modeling scenario"
      ],
      "misconception_signals": [
        "Overstates that more data always eliminates epistemic uncertainty"
      ],
      "simulator_behavior": [
        "Uses relational explanations and caveats",
        "Can answer comparison questions but may hesitate on unfamiliar applications"
      ]
    },
    "L4": {
      "description": "The user can apply epistemic uncertainty to new problems, choose when the concept is relevant, and reason about interventions such as collecting data or changing models.",
      "diagnostic_goal": "Check whether the user can use the concept in unfamiliar scenarios and decide when it applies.",
      "positive_signals": [
        "Uses epistemic uncertainty to reason about active learning or model selection",
        "Explains whether collecting more data is an appropriate response in a given scenario",
        "Distinguishes uncertainty reduction strategies from noise handling strategies"
      ],
      "negative_signals": [
        "May not critique deeper assumptions behind uncertainty estimates",
        "May not generate strong teaching examples or counterexamples without support"
      ],
      "misconception_signals": [
        "Assumes uncertainty estimates are automatically well-calibrated"
      ],
      "simulator_behavior": [
        "Applies the concept to novel but realistic problems",
        "Can justify when to use or avoid the concept"
      ]
    },
    "L5": {
      "description": "The user can critique, abstract, teach, and generate new examples or counterexamples involving epistemic uncertainty.",
      "diagnostic_goal": "Check whether the user can reason reflectively about assumptions, limitations, and generative uses of the concept.",
      "positive_signals": [
        "Designs examples, analogies, and counterexamples",
        "Critiques assumptions behind uncertainty estimation methods",
        "Explains how the concept shapes experimental or benchmark design"
      ],
      "negative_signals": [],
      "misconception_signals": [],
      "simulator_behavior": [
        "Gives compact but nuanced explanations",
        "Can teach the concept and point out hidden assumptions in questions or papers"
      ]
    }
  },
  "source": ["textbook_chapter_3", "survey_section_2.1"]
}
```

## Knowledge Edge

### Knowledge Edge v1 Design

#### 概念边界

`Knowledge Edge` 是用户无关的知识关系。它连接两个 `Knowledge Node`，用于表达概念之间的组成、认知依赖、支撑或对比关系。

`Knowledge Edge` 不连接 mastery level，不包含用户状态，不包含诊断题或 probe strategy。诊断目标仍属于 `Knowledge Node`；用户掌握情况仍属于 `User Knowledge State`。

``` text
Knowledge Edge
= 两个 Knowledge Node 之间的客观领域关系

Curation Confidence
= 图谱作者对这条关系成立的置信度

Knowledge Edge Weight
= 这条关系在知识结构中的强度
```

#### Knowledge Edge 类型

v1 严格限制 edge type，只允许以下四种：

| 类型 | 方向 | 含义 |
| --- | --- | --- |
| `part_of` | source 是部分，target 是整体 | source 是 target 的结构性组成部分，不表示 topic/category 归属 |
| `prerequisite_for` | source 是前置概念，target 是依赖概念 | 缺失 source 会稳定削弱或阻碍 target 的高层次理解，但不表示完全无法达到低层次理解 |
| `supports` | source 支撑 target | source 能增强对 target 的解释、迁移或诊断信心，但不是前置依赖 |
| `contrasts_with` | 对称关系，存储时按 node id 字典序放置 source/target | 两个概念常通过边界、失败模式或差异对比来互相澄清 |

不使用 `related_to`、`used_for` 或自由字符串关系，因为它们太宽泛，不利于 benchmark 评估。

`part_of` 只表达组成关系，不表达分类树或主题归属。`Knowledge Node` 本身没有内置层级划分，因此一个 node 可以通过多条 `part_of` 边成为多个整体的组成部分。

`prerequisite_for` 表达认知依赖，不是严格数学意义上的必要条件。用户可以在缺少前置概念时对目标概念达到 L1/L2，但通常难以稳定达到 L3+。

`supports` 和 `prerequisite_for` 的判别规则：

``` text
如果缺失 source 会让 target 的 L3+ 通常站不住，使用 prerequisite_for。
如果缺失 source 只是让解释更弱、更浅或少一个视角，使用 supports。
```

`contrasts_with` 是语义对称关系，但只存储一条边。存储时按 node id 字典序排列 `source` 和 `target`，避免重复边。

#### Knowledge Edge 最小字段

v1 中，`Knowledge Edge` 的最小字段为：

``` json
{
  "id": "edge_epistemic_uncertainty_prerequisite_for_active_learning",
  "source": "epistemic_uncertainty",
  "target": "active_learning",
  "type": "prerequisite_for",
  "rationale": "Understanding reducible model uncertainty helps explain why active learning queries informative samples.",
  "weight": 0.85,
  "curation_confidence": 0.95
}
```

字段含义：

- `id`：稳定的机器可读标识，推荐格式为 `edge_{source}_{type}_{target}`。
- `source`：源 `Knowledge Node` 的 id。
- `target`：目标 `Knowledge Node` 的 id。
- `type`：固定为 `part_of`、`prerequisite_for`、`supports` 或 `contrasts_with` 之一。
- `rationale`：说明这条客观知识关系为什么成立。它不描述用户证据，也不描述如何提问。
- `weight`：required，范围为 `0.0` 到 `1.0`，表示这条关系在知识结构中的强度。
- `curation_confidence`：required，范围为 `0.0` 到 `1.0`，表示图谱作者对这条关系成立的置信度。

`weight` 和 `curation_confidence` 含义不同：

``` text
weight
= 关系强度

curation_confidence
= 对关系标注有效性的置信度
```

后续算法可以按需派生：

``` text
effective_relationship_strength = weight * curation_confidence
```

但 `effective_relationship_strength` 是派生值，不存入 authored graph。

#### Authored Graph 与 Derived Relationship

v1 的 ground truth 只包含显式编写的 `Knowledge Edge`，不自动做传递闭包。

例如：

``` text
A prerequisite_for B
B prerequisite_for C
```

不自动推出：

``` text
A prerequisite_for C
```

传递、路径搜索或关系扩展可以作为后续代码中的派生机制，但不能回写或污染初始 authored graph。

低 `curation_confidence` 的边可以用于 authoring 阶段讨论，但不应未经审查就作为稳定 benchmark ground truth。

#### 不进入 Knowledge Edge v1 的字段

以下内容暂不进入 `Knowledge Edge` v1 schema：

- `source_refs`：edge 的出处暂不单独维护，v1 通过 required `rationale` 保持最小可审计性。
- `diagnostic_goal`、`probe_question`、`diagnostic_signals`：诊断设计属于 node、task 或 probe，不属于 edge 本体。
- `supports_level`、`applies_to_target_level`：edge 连接 node，不连接具体 mastery level。
- `userstate`、`edge_userstate`、`edge_understanding`：用户状态只维护 node-level state。
- `effective_relationship_strength`：运行时派生，不存储。
- inferred / transitive edge：推理得到的关系不是 authored graph 的一部分。

## Knowledge Graph 与 Knowledge Map

KnowAct 区分用户无关的 `Knowledge Graph` 和用户相关的 `Knowledge Map`。

``` text
Knowledge Graph
= 用户无关的客观知识结构
= nodes + edges

Knowledge Map
= 某个用户或被测 agent 重建出的知识状态视图
= graph reference + userstate + evidence
```

`Knowledge Graph` 中的 node 和 edge 都是客观领域结构，不记录某个用户是否掌握它们。`Knowledge Map` 才记录用户状态。

v1 中，`userstate` 只描述用户对 `Knowledge Node` 的掌握，不描述用户对 `Knowledge Edge` 的掌握。edge 的作用是帮助 agent 在图上探索、选择诊断路径、理解概念之间的客观结构，而不是作为用户状态对象。

### Knowledge Graph 最小结构

``` json
{
  "nodes": [
    {
      "id": "epistemic_uncertainty",
      "name": "Epistemic Uncertainty",
      "type": "concept",
      "definition": "Uncertainty caused by lack of knowledge or limited data.",
      "diagnostic_goal": "Assess whether the user can distinguish reducible model uncertainty from irreducible data noise.",
      "levels": {},
      "source": ["textbook_chapter_3", "survey_section_2.1"]
    }
  ],
  "edges": [
    {
      "id": "edge_epistemic_uncertainty_prerequisite_for_active_learning",
      "source": "epistemic_uncertainty",
      "target": "active_learning",
      "type": "prerequisite_for",
      "rationale": "Understanding reducible model uncertainty helps explain why active learning queries informative samples.",
      "weight": 0.85,
      "curation_confidence": 0.95
    }
  ]
}
```

### User State 与 Evidence

`User Knowledge State` 不属于 `Knowledge Node`，但它应引用 node 和全局等级：

``` json
{
  "user_id": "u_001",
  "node_id": "epistemic_uncertainty",
  "mastery_level": "L2",
  "confidence": 0.72,
  "evidence_refs": ["ev_001", "ev_004"],
  "misconceptions": [
    "conflates_epistemic_uncertainty_with_data_noise"
  ],
  "unknowns": [
    "whether_user_can_apply_the_concept_to_active_learning"
  ]
}
```

`Evidence` 建议使用共享基础结构，但通过 `evidence_type` 和 `visibility` 区分用途。v1 中，evidence 只引用 `Knowledge Node`，不引用 `Knowledge Edge`：

``` json
{
  "id": "ev_001",
  "evidence_type": "ground_truth_profile",
  "visibility": "simulator_only",
  "node_id": "epistemic_uncertainty",
  "supports_level": "L2",
  "signal": "User can explain lack of data but confuses it with noise.",
  "source": "profile_authoring"
}
```

``` json
{
  "id": "ev_104",
  "evidence_type": "interaction_observation",
  "visibility": "tested_agent",
  "turn_id": "turn_03",
  "node_id": "epistemic_uncertainty",
  "supports_level": "L1",
  "contradicts_level": "L3",
  "observed_text": "I think it is just noise in the dataset.",
  "signal": "Conflates epistemic uncertainty with aleatoric uncertainty.",
  "confidence": 0.82
}
```

两类 evidence 的边界：

``` text
ground_truth_profile evidence
= 静态、隐藏、simulator-only
= 用于让用户模拟器保持一致知识画像

interaction_observation evidence
= 动态、随对话追加、tested-agent-visible
= 用于被测 agent 实时更新用户状态判断
```
