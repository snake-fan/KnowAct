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
  "source_locators": [
    {
      "source_id": "example_textbook",
      "locator": "chapter_3_section_3.2",
      "note": "Pages 45-47"
    }
  ]
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

每个 node 必须能追溯到选定的 authoritative source。v1 不接受凭常识现编的 candidate node inventory；candidate nodes 应从权威教材、课程材料、经典论文或术语表中抽取，并保留可定位的 source locator。

``` text
book / chapter / section / page
course / lecture / slide
paper / section / paragraph
reference / entry
```

source locator 简单指到即可，目标是让 benchmark author 能回到原始材料确认这个知识点确实出现过。v1 不要求在 node 中保存原文 quote、`evidence_span`、精确文本 offset 或完整摘录。

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
  "source_locators": [
    {
      "source_id": "example_textbook",
      "locator": "chapter_3_section_3.2",
      "note": "Pages 45-47"
    }
  ]
}
```

字段含义：

- `id`：稳定的机器可读标识。
- `name`：人类可读名称。
- `type`：v1 暂时只使用 `"concept"`，不扩展复杂 taxonomy。
- `definition`：概念定义。
- `diagnostic_goal`：该 node 的总体诊断目标，即这个概念整体要测什么。
- `levels`：固定包含 `L0` 到 `L5` 的对象。
- `source_locators`：知识点来源定位，用于证明该 node 是可追溯的知识单位。v1 中应使用结构化 source locator，而不是泛泛的字符串标签。

`source_locators` 只挂在 node 顶层。level 不单独维护 `source_locators`，因为 source locator 证明的是知识点本身可查，而不是每个掌握程度 rubric 的出处。

source locator 的推荐字段：

``` json
{
  "kind": "textbook",
  "title": "Authoritative source title",
  "edition": "optional",
  "chapter": "optional",
  "section": "optional",
  "pages": "optional",
  "url": "optional"
}
```

不同 source kind 可以使用不同定位字段，但必须足以让 benchmark author 回到原始材料核查该 node。

v1 的 source locator 不需要比人工 review 所需更精细。对于 textbook，chapter / section / pages 通常足够；对于课程材料，lecture / slide 通常足够；对于论文，section 或 paragraph 通常足够。`quote`、`evidence_span`、character offset 这类精确摘录可以出现在 workflow 调试日志或人工审核笔记中，但不进入 `Knowledge Node` schema。

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
- `quote`、`evidence_span`、exact text offset：v1 的 source locator 简单指到出处即可，不要求保存原文摘录或精确文本范围。
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
  "source_locators": [
    {
      "source_id": "example_textbook",
      "locator": "chapter_3_section_3.2",
      "note": "Pages 45-47"
    }
  ]
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

v1 的 edge proposal 采用 precision-first 策略。`candidate_edges.json` 应优先包含少量、明确、可解释的 canonical edges，而不是尽量召回所有可能相关的 node pair。只有当关系能被归入 `part_of`、`prerequisite_for`、`supports` 或 `contrasts_with`，并且能写出清楚的 `rationale` 时，才应进入 `candidate_edges.json`。

如果两个 node 只是同章出现、主题相近、可能有关，但说不清具体关系类型或 rationale，应先省略，而不是用 `supports` 兜底。低置信或弱关系可以留在 workflow 调试记录或人工讨论中，但不进入最终 edge list。

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
- `curation_confidence`：required，范围为 `0.0` 到 `1.0`，表示这条关系成立的置信度。candidate 阶段可以由 graph authoring workflow 给出初始建议值；review 之后，该字段表示 benchmark author 接受或修订后的值。

在 candidate 阶段，v1 不设置固定的 `curation_confidence` 数值阈值。一个 edge 是否进入 `candidate_edges.json`，主要由 precision-first 策略决定：它必须属于 canonical edge type，并且有清楚的 `rationale`。`curation_confidence` 保留为人工 review 和后续校准信号，而不是硬过滤条件。

如果 `curation_confidence` 低是因为关系类型或 rationale 本身说不清，应按 precision-first 策略省略该 edge；如果关系足够清楚，但 authoring workflow 对细节仍有不确定性，则可以保留 `curation_confidence` 供 review 判断。

candidate 和 authored edge 使用同一个字段名，避免 schema 分裂：

``` text
candidate_edges.json
= graph authoring workflow suggested curation_confidence

authored_edges.json
= benchmark-author reviewed curation_confidence
```

`weight` 和 `curation_confidence` 含义不同：

``` text
weight
= 关系强度

curation_confidence
= 对关系标注有效性的置信度。candidate 阶段可由 agent 建议；authored 阶段由 benchmark author 审核接受或修订。
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

低 `curation_confidence` 的边可以用于 authoring 阶段讨论，但不应未经审查就作为稳定 benchmark ground truth。v1 暂不规定低于某个 `curation_confidence` 数值就必须排除；是否进入 candidate edge list 仍以 canonical type 和 rationale clarity 为准。

### Graph Authoring Boundary

LLM workflow 可以用于从选定的权威教材、课程材料或论文中生成 `Candidate Knowledge Graph`，但 candidate graph 不能直接进入 v1 evaluation。benchmark author 必须审核 nodes、edges、rationales、weights、curation confidence 和 mastery rubrics 后，才能将其发布为 `Authored Knowledge Graph`。

v1 的 source-grounded node skeleton list 必须先从 authoritative source 抽取。每个 node skeleton 都应带 source locator；不要在没有 source locator 的情况下凭常识现编 node 清单。后续 `Node Rubric Authoring Agent Step` 再把 skeleton 补全为完整 candidate node。

v1 的抽取过程不以手工编写 candidate node inventory 为主，而是先实现 `Graph Authoring Agent Workflow`。该 workflow 通过项目自写的轻量 agent frame 调用模型 API，直接读取 authoritative PDF 或 source material，分步骤执行知识点抽取、定位出处、node rubric 编写、合并和关系提议。

workflow 的最终可审阅输出只包含两个 JSON list 文件：

``` text
candidate_nodes.json = Knowledge Node[]
candidate_edges.json = Knowledge Edge[]
```

`candidate` 只允许出现在文件名、目录名或审阅状态中。JSON 对象内容本身不写 `candidate`、`candidate_status`、`review_status` 或类似字段；node 和 edge 都直接使用正常的 `Knowledge Node` / `Knowledge Edge` schema。

`candidate_nodes.json` 的内容是 node list。每个对象应包含完整的 node 诊断结构：

``` json
{
  "id": "epistemic_uncertainty",
  "name": "Epistemic Uncertainty",
  "type": "concept",
  "definition": "Uncertainty caused by lack of knowledge, limited data, or incomplete model understanding.",
  "diagnostic_goal": "Assess whether the user can distinguish reducible model uncertainty from irreducible data noise and use that distinction in reasoning about model behavior.",
  "levels": {
    "L0": {},
    "L1": {},
    "L2": {},
    "L3": {},
    "L4": {},
    "L5": {}
  },
  "source_locators": [
    {
      "source_id": "isl_python",
      "locator": "chapter_3_section_3.2",
      "note": "Optional reviewer note"
    }
  ]
}
```

`candidate_edges.json` 的内容是 edge list。每个对象应直接表达 node 之间的关系：

``` json
{
  "id": "edge_aleatoric_uncertainty_contrasts_with_epistemic_uncertainty",
  "source": "aleatoric_uncertainty",
  "target": "epistemic_uncertainty",
  "type": "contrasts_with",
  "rationale": "These nodes are commonly understood by comparing reducible uncertainty from limited knowledge with irreducible randomness or noise.",
  "weight": 0.8,
  "curation_confidence": 0.9
}
```

edge 对象不复制 node 的 rubric 结构。也就是说，`name`、`definition`、`diagnostic_goal`、`levels` 和 node-level source locator 属于 `candidate_nodes.json`；`candidate_edges.json` 只描述两个 node 之间的关系。注意 edge 字段中的 `source` 表示 source node id，不是 textbook source locator。

校验日志、冲突说明或中间 reasoning 可以作为 workflow 内部调试信息存在，但不属于最终答案 schema；最终交付给 benchmark author 审阅的就是这两个 JSON list 文件。

Graph authoring 是一个 `Graph Authoring Agent Workflow`，其中包含多个 agent steps。node 不在 extraction 阶段一次性生成完整 schema，而是分成 source-grounded skeleton 和 node rubric 两个阶段：

``` text
Node Extraction Agent Step
= authoritative PDF / source material
→ source reading
→ source-grounded node skeleton extraction
→ duplicate / merge pass
→ source locator validation
→ source grounding note extraction
→ source-grounded node skeleton list

Node Rubric Authoring Agent Step
= source-grounded node skeleton list
+ source locators and source grounding notes
+ global MasteryScale
→ diagnostic_goal drafting
→ L0-L5 level rubric drafting
→ positive / negative / misconception signal drafting
→ simulator_behavior drafting
→ node JSON list

Edge Proposal Agent Step
= complete candidate_nodes.json
+ node rubrics
+ source locators and source grounding notes
→ candidate edge proposal
→ precision-first filtering
→ edge rationale drafting
→ edge weight / curation confidence suggestions
→ edge JSON list

Graph Authoring Agent Workflow output
= candidate_nodes.json
+ candidate_edges.json
→ human review
```

`Node Rubric Authoring Agent Step` 的 v1 输入边界应保持收窄：它只参考 source-grounded node skeleton、source locator、source grounding notes，以及全局 `MasteryScale`。它不接收 full Parsed Source Markdown 或 source-material text 参数，也不使用当前 candidate graph 中尚未审核的邻近 nodes、candidate edges 或 graph traversal context 来生成 rubric。

如果 authoritative source 本身通过对比或依赖关系解释该概念，rubric 可以反映这些 source-grounded 关系；但不能因为 workflow 已经临时生成了一条 candidate edge，就反过来把这条未审核关系写进 node 的诊断标准。

`Edge Proposal Agent Step` 的输入边界与 rubric step 不同。edge proposal 发生在完整 candidate nodes 可用之后，因此 v1 允许它参考 `candidate_nodes.json` 中的完整 node rubrics，包括 `diagnostic_goal`、L0-L5 `levels`、diagnostic signals 和 `simulator_behavior`，以及 workflow intermediate artifacts 中的 source locators 和 source grounding notes，来判断 `part_of`、`prerequisite_for`、`supports`、`contrasts_with` 等关系。它同样不接收 full Parsed Source Markdown 或 source-material text 参数。

`Edge Proposal Agent Step` 的输出策略是 precision-first。它应省略弱相关、rationale 不清、类型归属不清的关系，避免把 `candidate_edges.json` 变成“可能相关”的候选池。`supports` 也必须表达具体的解释、迁移或诊断贡献，不能作为泛化的 relatedness 标签使用。

v1 不为 `candidate_edges.json` 设置固定 `curation_confidence` 阈值。`curation_confidence` 必须填写，但它用于 review 排序、校准和后续分析，不作为进入 edge list 的硬门槛。阈值策略等实际生成若干轮 candidate graph 后再决定。

这种方向不能反过来：node rubric 不由 candidate edge 生成，但 candidate edge 可以参考已经生成的 node rubric。edge proposal 仍然只是 candidate output，不能绕过 benchmark-author review。

因此，node extraction、node rubric authoring 和 edge generation 可以由不同 agent step 分别完成，但它们属于同一个 graph authoring workflow，而不是多个互相独立的 workflow。该 workflow 的最终输出仍然是两个 JSON list 文件，不直接自动接受为 `Authored Knowledge Graph`。

benchmark author 完成人工 review 后，v1 仍然分别存储 graph data：

``` text
authored_nodes.json = reviewed Knowledge Node[]
authored_edges.json = reviewed Knowledge Edge[]
```

也就是说，candidate 阶段和 authored 阶段都保持 nodes / edges 分文件存储；review 过程可以通过复制、改名或发布目录来完成状态转换，但不把 node list 和 edge list 合并成一个大 JSON。

v1 暂不规定这些文件在仓库或数据集中的目录结构。当前只固定文件内容 schema 和 nodes / edges 分文件存储；具体 `Graph File Layout` 由 benchmark author 后续指定。代码和文档在该布局明确前不应假设固定目录路径。

如果后续需要稳定记录 graph id、版本、source、文件路径或发布时间，可以额外使用轻量 `graph_manifest.json`：

``` json
{
  "graph_id": "kg_classical_supervised_ml_algorithms_v1",
  "domain": "classical_supervised_ml_algorithms",
  "version": "v1",
  "nodes_file": "authored_nodes.json",
  "edges_file": "authored_edges.json",
  "source": [
    {
      "kind": "textbook",
      "title": "An Introduction to Statistical Learning with Applications in Python"
    }
  ]
}
```

`graph_manifest.json` 只负责绑定元数据和文件引用，不内联 nodes / edges，也不承载 scoring override。

v1 的 primary authoritative source 选定为：

``` text
An Introduction to Statistical Learning with Applications in Python
official site: https://www.statlearning.com/
official PDF: https://hastie.su.domains/ISLP/ISLP_website.pdf
```

v1 只从其中与 `classical_supervised_ml_algorithms` 相关的章节抽取 candidate nodes：

``` text
included:
- Statistical Learning
- Linear Regression
- Classification
- Resampling Methods
- Linear Model Selection and Regularization
- Tree-Based Methods
- Support Vector Machines

excluded from v1:
- Deep Learning
- Unsupervised Learning
- Survival Analysis
- Multiple Testing
```

``` text
selected authoritative source
→ Graph Authoring Agent Workflow
   → Node Extraction Agent Step
→ source-grounded node skeleton list
   → Node Rubric Authoring Agent Step
→ candidate_nodes.json
   → Edge Proposal Agent Step
→ candidate edge proposals
+ candidate_edges.json
→ benchmark-author review
→ authored_nodes.json
+ authored_edges.json
→ Authored Knowledge Graph
→ v1 evaluation
```

因此，graph generation workflow 属于 authoring pipeline，不属于 evaluation runtime。

同样，LLM workflow 可以生成 `Candidate Knowledge Map`，但 candidate map 不能直接作为评分 reference。benchmark author 必须审核每个 node-level `User Knowledge State` 的 consistency、plausibility、edge-aware constraints 和 evidence support 后，才能将其发布为 `Ground-Truth Knowledge Map`。

``` text
Authored Knowledge Graph
→ LLM-assisted map authoring
→ Candidate Knowledge Map
→ benchmark-author review
→ Ground-Truth Knowledge Map
→ v1 evaluation
```

因此，map generation workflow 也属于 authoring pipeline，不属于 evaluation runtime。

Persona、background、preferences 和 task goal 属于 `Profile Context`。它们可以用于生成更一致的 `Candidate Knowledge Map`，也可以作为 `background_fact` evidence 的来源，并影响 simulator 的表达方式、熟悉例子和自述内容。它们必须与 `Ground-Truth Knowledge Map` 保持一致，但不进入 v1 的 `episode_mastery_distance` 主评分。

``` text
Profile Context
→ constrains Candidate Knowledge Map generation
→ supports evidence such as background_fact
→ shapes simulator answer style

Profile Context
↛ episode_mastery_distance
```

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
      "source_locators": [
        {
          "source_id": "example_textbook",
          "locator": "chapter_3_section_3.2",
          "note": "Pages 45-47"
        }
      ]
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

`User Knowledge State` 不属于 `Knowledge Node`，但它应引用 node 和全局等级。无论它出现在 `Ground-Truth Knowledge Map` 还是 `Reconstructed Knowledge Map` 中，v1 都要求它通过 `evidence_refs` 指向至少一条可用的 `Evidence Record`：

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

在 `Ground-Truth Knowledge Map` 中，`evidence_refs` 可以引用 `simulator_only` 或 `evaluator_only` 的 `ground_truth_profile` evidence。

在 `Reconstructed Knowledge Map` 中，`evidence_refs` 只能引用被测 agent 可见的 evidence，通常是 `visibility: "tested_agent"` 的 `interaction_observation`。被测 agent 不能引用 hidden reference evidence 来支撑自己的推断。

`Evidence` 在 v1 中使用统一的 `Evidence Record` 结构。`ground_truth_profile` evidence 和 `interaction_observation` evidence 不是两套 schema，而是同一结构在不同 `evidence_type` 与 `visibility` 下的实例。

v1 中，evidence 只引用 `Knowledge Node`，不引用 `Knowledge Edge`。所有 `Evidence Record` 至少包含：

``` text
id
evidence_type
evidence_kind
visibility
node_id
signal
```

初始 `evidence_type`：

``` text
ground_truth_profile
= 静态画像或模拟画像中的依据

interaction_observation
= episode 中可见对话产生的观察
```

`evidence_type` 回答证据来自哪里、服务于什么生命周期；`evidence_kind` 回答证据以什么诊断形态支持知识状态判断。二者不要混用。

初始 `evidence_kind`：

``` text
prior_answer
= 用户曾经如何回答相关问题

worked_example
= 用户能或不能解决的具体例子

self_report
= 用户自述知道或不知道什么

misconception_trace
= 用户暴露出的具体误解、混淆或错误推理路径

background_fact
= 用户背景中能支持知识状态判断的事实
```

如果一条观察同时符合多个 kind，应选择最能解释该证据诊断价值的主 kind；如果需要分别支持不同判断，应拆成多条 `Evidence Record`。

初始 `visibility`：

``` text
simulator_only
= hidden reference data，可约束 user simulator，不对 tested agent 可见

tested_agent
= 来自可见交互历史，可被 tested agent 用于更新推断

evaluator_only
= 只供 benchmark runner 或 evaluator 使用的参考数据
```

示例：

``` json
{
  "id": "ev_001",
  "evidence_type": "ground_truth_profile",
  "evidence_kind": "misconception_trace",
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
  "evidence_kind": "prior_answer",
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
= 静态、隐藏、simulator-only 或 evaluator-only
= 用于让用户模拟器保持一致知识画像

interaction_observation evidence
= 动态、随对话追加、tested-agent-visible
= 用于被测 agent 实时更新用户状态判断
```

不要把 `Evidence Record` 当作 LLM 的 hidden chain-of-thought。`evidence_kind` 和 `signal` 都应描述可审计的用户知识痕迹，例如用户曾经的回答、解题表现、自述、误解迹象或背景事实。

`Reconstructed Knowledge Map` 中的状态如果没有 evidence 支撑，应视为 unsupported inference。v1 可以选择拒收这类状态，或在 scoring 时单独惩罚。

### V1 Scoring Boundary

v1 的主评分应保持简单：自动比较 `Ground-Truth Knowledge Map` 和 `Reconstructed Knowledge Map` 中可量化的 `User Knowledge State` 字段，尤其是 `mastery_level` distance。可以辅助比较 `confidence`、`misconceptions` 或 `unknowns`，但不引入新的 evaluator agent 或 LLM judge 来主观判断重建画像质量。

v1 的每个 `Evaluation Episode` 应由显式 manifest 声明。manifest 负责绑定该 episode 使用的 graph、hidden map、profile context、turn budget、interaction rule 和 scoring profile：

``` json
{
  "episode_id": "ep_active_learning_u001",
  "knowledge_graph_id": "kg_active_learning_v1",
  "ground_truth_map_id": "gt_u001",
  "profile_context_id": "profile_u001",
  "max_turns": 8,
  "interaction_rule": "one_diagnostic_question_per_turn",
  "scoring_profile": "squared_mastery_distance_v1"
}
```

`profile_context_id` 可以为空，但如果存在，必须与 `Ground-Truth Knowledge Map` 保持一致。runner 应使用 manifest 校验 graph、map、turn budget 和 scoring rule 是否属于同一个 episode。

v1 只有一个固定 scoring profile：`squared_mastery_distance_v1`。Manifest 可以引用它，但不能按 episode 改写 distance function、missing prediction penalty 或 episode aggregation 规则。该 profile 固定包含：

``` text
L0-L5 -> 0-5
valid prediction distance = squared distance
missing_prediction_distance = 36
episode_mastery_distance = mean node distance
unsupported_inference_rate = separately reported
```

`mastery_level_distance` 是 v1 的主比较信号。v1 默认使用简单的平方距离：先将 L0-L5 映射为 0-5 分，再计算预测等级与真实等级的距离平方。

``` text
level_score:
L0 = 0
L1 = 1
L2 = 2
L3 = 3
L4 = 4
L5 = 5

mastery_level_distance =
  (level_score[predicted_level] - level_score[ground_truth_level]) ^ 2
```

`mastery_distance_fn` 至少满足：

``` text
distance(Lx, Lx) = 0
distance(Lx, Ly) >= 0
missing_prediction_distance = 36
```

`distance == 0` 可以作为 exact mastery bonus 或派生统计项，但不需要作为另一套独立主指标。

每个 `Evaluation Episode` 使用一个 `Episode Knowledge Graph`。v1 不额外引入 `scored_node_ids` 或评分节点子集；默认该 graph 上的所有 `Knowledge Node` 都参与 `mastery_level` 评分：

``` text
scoring scope = Episode Knowledge Graph.nodes
```

因此，v1 有明确的 map coverage requirement：

``` text
Ground-Truth Knowledge Map
= must contain User Knowledge State for every node in Episode Knowledge Graph

Final Reconstructed Knowledge Map
= should contain User Knowledge State for every node in Episode Knowledge Graph
= missing nodes are accepted by the runner but scored as missing_prediction
```

也就是说，ground truth map 如果缺少 episode graph 中的 node，应视为 benchmark data validation failure；final reconstructed map 如果缺少 node，则进入 scoring，并按 `missing_prediction_distance = 36` 处理。

每个 `Evaluation Episode` 应显式配置 `max_turns` 作为 turn budget。v1 不从 graph node 数量自动推导 `max_turns`，因为图谱粒度和交互预算是两个不同设计维度。benchmark author 应根据 episode 难度、目标领域和诊断成本设置最大轮次。

v1 中，一个 `Interaction Turn` 定义为：

``` text
one tested-agent diagnostic question
+ one user simulator answer
```

每轮只允许一个主要 `Diagnostic Question`。被测 agent 可以用一句很短的上下文铺垫问题，但不能在同一轮打包多个独立问题；user simulator 也只回答该轮的主要诊断问题。这样 `max_turns` 才能稳定表示诊断机会数量。

`User Simulator` 应使用 hidden `Ground-Truth Knowledge Map`、`simulator_only` evidence、当前 `Diagnostic Question` 和对话历史来生成自然语言回答。它不是状态查询接口，不应主动暴露：

``` text
完整 userstate table
mastery_level label，例如 “我是 L2”
hidden evidence id
benchmark scoring fields
```

simulator answer 应表现为用户对问题的自然回答，而不是结构化 ground-truth dump。

simulator answer 可以包含自然模糊性，例如：

``` text
犹豫
部分正确
自我修正
说不知道
暴露误解
```

但这种模糊必须受 hidden `Ground-Truth Knowledge Map` 和 evidence 约束。simulator 不能随机改变真实掌握水平，不能给出与 hidden evidence 明显冲突的答案，也不能用模糊回答逃避所有诊断问题。

如果 `Reconstructed Knowledge Map` 缺少某个 node 的 `User Knowledge State`，v1 将该 node 记为 `missing_prediction`。`missing_prediction` 不能等同于 `L0`，因为 `L0` 表示用户真实处于无有效理解或错误识别状态，而 missing 表示被测 agent 没有给出判断。

推荐评分语义：

``` text
ground truth has node A
reconstructed map lacks node A

prediction_status = missing_prediction
mastery_distance = 36
unsupported_inference = not applicable
```

合法 L0-L5 预测中的最大平方距离是 25，即 L0 与 L5 之间的距离。`missing_prediction_distance = 36` 让缺失预测比任何有效但错误的 mastery prediction 惩罚更重，同时仍然通过 `missing_prediction_rate` 单独报告覆盖问题。

v1 的 episode-level 主结果是所有 nodes 的平均 mastery distance，越低越好：

``` text
episode_mastery_distance =
  mean(node_mastery_distance for node in Episode Knowledge Graph.nodes)
```

推荐报告：

``` text
episode_mastery_distance
missing_prediction_rate
unsupported_inference_rate
exact_mastery_rate 或 exact_mastery_bonus
confidence_calibration_error（可选）
misconception_detection（可选）
```

`Evidence Record` 的作用是让 `Reconstructed Knowledge Map` 中的掌握程度判断更有依据、更准确，并支持审计 unsupported inference。Evidence 本身不应把 v1 评分变成另一轮自然语言评价任务。

如果 `Reconstructed Knowledge Map` 给出了某个 node 的 `User Knowledge State`，但没有引用任何 tested-agent-visible `Evidence Record`，v1 将该状态记为 `unsupported_inference`。`unsupported_inference` 不覆盖 `mastery_level_distance`，而是作为单独诊断指标或惩罚项报告。

推荐评分语义：

``` text
reconstructed map predicts node A mastery_level
reconstructed state has no visible evidence_refs

mastery_level_distance =
  (level_score[predicted_level] - level_score[ground_truth_level]) ^ 2
unsupported_inference = 1
```

v1 只要求被测 agent 在 episode 结束后提交 `Final Reconstructed Knowledge Map`，主评分只使用这个最终 map。每轮 inferred map snapshot、uncertainty notes 或 question selection rationale 可以作为 `Reconstruction Trace` 保留，用于调试和错误分析，但不是 v1 主评分的必需输入。
