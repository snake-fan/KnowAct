# 最终方法：KnowAct 知识图谱生成

[English](./final_kg_generation_method.md)

状态：当前实现的最终整合说明，已与 2026-08-01 的仓库实现对齐。

这里的“最终”表示它是当前系统的规范方法说明，不表示图谱质量、心理测量效度或 EDGA 研究假设已经获得最终实证确认。

## 1. 方法定位

KnowAct 不是把文本通用地转换成三元组，而是构建一个小型、来源可追踪的诊断知识图谱，用它定义 benchmark 可以诊断哪些知识。

该图谱与用户无关。用户掌握程度、误解、证据和重建状态属于 Knowledge Map，不能进入知识节点或知识边。

当前实现名为 `Graph Authoring Agent Workflow`。更准确的描述是：**来源约束、范围条件化、验证门控的诊断图谱构建方法**。

EDGA 是待验证的研究表述，并不等同于当前实现的全部细节。第 9 节会区分已实现 workflow 与 EDGA 假设。

## 2. 运行契约

该 workflow 围绕四条不变量设计：

- 来源主张必须能追踪到经过完整性校验的固定 Markdown。
- 节点发现、规范化、rubric 编写和边提议必须分开决策。
- 模型输出在人工显式 promotion 前始终只是 candidate data。
- Evaluation runtime 只能读取不可覆盖的 reviewed graph version。

端到端路径如下：

```text
固定来源 + 版本化 scope metadata
  -> 确定性切分
  -> 带精确 excerpt 的局部节点草稿
  -> 全局 skeleton reconciliation
  -> 角色分离的 skeleton verification
  -> L0-L5 诊断 rubric 编写
  -> 精确性优先的边提议
  -> 结构校验与 candidate 导出
  -> benchmark author 编辑与审核
  -> 显式、不可覆盖的 promotion
```

## 3. 固定输入与范围

### 3.1 来源目录

当前研究入口只接受 `Economy`、`ISLP` 和 `OSTEP`。Benchmark author 在 workflow 外手工准备 UTF-8 Markdown，并放入 `storage/source_materials/{source_id}/`。

Catalog 根据 `metadata.json` 定位文件。生成前，代码校验路径边界、记录的字节数和 SHA-256。PDF 到 Markdown 的转换不属于 KnowAct。

### 3.2 Metadata 管理的 scope

每个来源都拥有版本化 `GraphAuthoringScope`，其中包含：

- aspect 名称与描述；
- 至少 50 道唯一的代表性诊断任务；
- 明确的排除主题；
- 节点数软目标；
- 节点数硬上限。

当前三个来源以约 20 个节点为目标，上限为 24。目标不是配额，不能为了凑数加入弱节点或重复节点。

API 只接收 `source_id`、可选 `run_id` 和 `client_provider`。Domain、scope、任务、排除项和节点预算均由后端加载，client 不能覆盖。

## 4. 生成流程

### 阶段 0：解析并校验来源

后端加载来源 metadata，要求 `benchmark_domain == source_id`，校验文件大小和哈希，并构造一个结构化 `SourceMaterial`。

该阶段失败时不会启动 candidate run。一次运行因此绑定到固定本地来源，而不是上传文件或嵌入 prompt 的文档。

### 阶段 1：确定性切分

本地代码解析 Markdown 标题，保留最多三级 heading path，移除窄范围结构噪声，并把相邻章节组合为有界窗口。

当前默认值为最小 50,000、目标 100,000、最大 150,000 字符，段落重叠为 0。超大章节会尽量按段落边界切分。

Segment 按文档顺序获得 `seg_000001` 一类的 run-local 确定性 id，并记录可供审核的位置、source locator 和 `char_count`。

切分不是 LLM 决策。完整 segment text 只保存在 replay/debug intermediate artifact 中。

### 阶段 2：Segment 级节点抽取

每个 segment 与冻结的 scope 一起交给 Node Extraction Agent Step。最多可并发请求八个 segment，但输出会按原始 segment 顺序重新组装。

该步骤只返回薄草稿：名称、定义、source locator、grounding note 和短 `evidence_excerpt`。它不能编写 rubric、边、难度标签或用户状态。

每个 segment 最多返回 12 个草稿。无可诊断概念的有效 segment 可以返回空列表；若所有 segment 都没有草稿，则整次运行失败。

代码会检查 excerpt 是否出现在给定 segment 中，并只对空白、换行、断词和可识别的 PDF 页边注入做窄范围归一化。

每个 segment 最多有三次 contract attempt。只有草稿超量或 excerpt membership 失败会触发完整局部重试；解析、schema 及后续失败都保持 fail-closed。

### 阶段 3：全局 Skeleton Reconciliation

一个全局 reconciliation step 读取全部薄草稿和冻结的 scope。它去重、合并、轻量拆分、移除弱项，并选择紧凑的全图概念集合。

它读取结构化草稿及其 provenance，不读取完整 source text。每个输出必须保留 supporting draft id、segment id、locator、未改写 excerpt 和 merge/split note。

硬上限通过校验执行，不允许截断。最终 node id 从 canonical name 确定性派生；发生冲突时直接报错，不能随意加后缀。

### 阶段 4：Skeleton Verification

独立角色的 verifier 会在 rubric 与 edge authoring 前审核每个 reconciled skeleton。输入包含 scope、定义、locator、grounding note 和 excerpt，但不包含完整来源。

只有 grounding 为 `supported`、scope 为 `in_scope`，且 diagnostic value 为 `high` 或 `medium` 的 skeleton 才能保留。每个输入 id 必须恰有一项决策。

这里实现的是角色与输入分离，并不保证模型独立。当前 provider wiring 可能让 proposer 和 verifier 使用同一个 model client。

### 阶段 5：诊断 Rubric 编写

通过 verification 的 skeleton 按每批八个处理。Rubric Agent 读取 skeleton 字段和全局 Mastery Scale，不读取完整来源、未审核邻居上下文或 candidate edges。

模型只写 rubric patch：`diagnostic_goal`、节点特定的 `L0`-`L5` 描述、可观察 `diagnostic_signals` 和 `simulator_behavior`。

Workflow code 将 patch 与来源约束的 id、名称、定义、类型和 locator 合并。模型不会重新复制或控制这些 grounded fields。

### 阶段 6：精确性优先的边提议

Edge Proposal Agent 在完整 candidate nodes 产生后运行。它可以读取 node rubric 与来源约束上下文，但不能修改节点或表达用户状态。

只允许四种 edge type：

- `part_of`；
- `prerequisite_for`；
- `supports`；
- `contrasts_with`。

弱相关、仅同主题或方向不明确的节点对应被省略。空 edges 合法。`curation_confidence` 是模型建议，不是自动准入阈值。

代码会规范化 `contrasts_with` 的端点顺序，然后校验完整图结构。

### 阶段 7：Candidate 校验与导出

阻塞校验检查 node id 唯一性、source locator、完整诊断字段、精确的 `L0`-`L5` keys、非空 signals、合法 endpoint、edge type 和整体图结构。

最终供审核的 payload 只有：

- `candidate_nodes.json`；
- `candidate_edges.json`。

`workflow_log.json`、`intermediate/` 和 `agent_traces/` 是审计与调试 sidecar。它们不会改变 candidate 生命周期，也不是 reviewed benchmark data。

### 阶段 8：Benchmark Author 审核与 Promotion

内部 workbench 可以加载并编辑 candidate graph。保存操作会在结构校验通过后覆盖 candidate node 和 edge lists。

Confirm 会先保存当前编辑、重新校验图谱、指定新 version，并发布到 `benchmark/domains/{domain}/graphs/{version}/` 的不可覆盖 snapshot。

Reviewed snapshot 包含 `authored_nodes.json`、`authored_edges.json` 和 `graph_manifest.json`。已有 version 不可覆盖。

只有显式 promotion 会把运行状态从 candidate 改为 reviewed。Runtime loader 会拒绝 candidate run directory。

## 5. 可追踪性与失败语义

每个成功边界都有结构化 intermediate artifact。每个 agent step 都记录 raw model output 与 parser output；segment 和 batch step 还会保留分项 trace。

Workflow 保持 fail-closed。它不会静默修复 parser failure、超预算 reconciliation、不完整 rubric、非法 endpoint 或图结构错误。

并发只影响吞吐，不改变组装顺序。Segment id、draft id、rubric batch order 和导出列表相对于来源顺序及已接受模型输出保持稳定。

Candidate 与 reviewed data 通过路径和 loader 显式分离。生命周期状态不写入 node 或 edge object。

## 6. 当前校验能够证明什么

当前实现能够证明：

- 运行开始时的 source file identity 与完整性；
- extraction excerpt 在对应 segment 中机械出现；
- draft 到 reconciled skeleton 的 provenance 一致；
- node rubric 结构完整且 graph structure 合法；
- promotion 是显式且不可覆盖的；
- runtime 不会读取 candidate graph directory。

这些检查支持可审计性与 schema reliability，但不能单独证明语义正确性或科学效度。

## 7. 当前快照

截至 2026-08-01 的检查结果，仓库中三个固定 scope 都存在成功 candidate run：

- `Economy`：22 个节点、20 条边；
- `ISLP`：21 个节点、29 条边；
- `OSTEP`：24 个节点、28 条边。

被检查的 workspace 中没有这三个 domain 的 `graphs/{version}/` reviewed snapshot。因此这些数量描述的是 candidate，而不是 benchmark ground truth。

Experiment 01 提供冻结的离线审核页、双 reviewer 对比和 adjudication export。这些 JSON submission 是科学审计记录，不会执行 operational graph promotion。

## 8. 已知局限

### 8.1 文本出现不等于语义蕴含

Exact excerpt membership 只能证明文本在 segment 中出现，不能证明它支持 node definition、粒度选择或诊断解释。

### 8.2 Verification 并非完全独立

Verifier 拥有不同角色和受限输入，但当前 wiring 可以复用同一 provider 和 model。没有跨模型或人工协议时，不能宣称独立验证。

### 8.3 切分可能丢失边界上下文

零重叠减少重复和成本，但跨越 segment boundary 的概念可能被漏掉。字符数也只是粗粒度 context proxy。

### 8.4 Rubric 是测量产物

概念有来源依据，不代表六级 mastery rubric 已被验证。Rubric 清晰度、专家一致性和心理测量表现需要单独评估。

### 8.5 Edge 的证据语义有限

Edge rationale、weight 和 confidence 由模型编写。结构校验只检查合法性与 endpoint，不检查来源蕴含或教学关系效度。

### 8.6 Candidate 编辑会削弱 provenance

Workbench 允许人工编辑。保存和 promotion 会对编辑后的图做结构校验，但不会把每项编辑重新绑定到原始 extraction 与 reconciliation evidence。

### 8.7 Recall 未知

当前 workflow 更容易评估已提议项目的质量，而不是漏掉的概念。尚无锁定的独立 reference subset 来估计概念或边的 recall。

### 8.8 下游收益尚未测量

当前实现不能证明它优于 one-shot generation，也不能证明它降低审核成本、提高 simulator validity 或稳定 tested-agent ranking。

## 9. 已实现方法与 EDGA 的边界

当前 workflow 已实现 source integrity、局部抽取、全局 canonicalization、verifier 角色、结构化 rubric、precision-first edges、审计 artifacts 和人工 promotion。

拟议 EDGA 方向还包含更强的主张与机制：真正独立的 verification、语义蕴含检查、typed repair、quarantine、风险排序的专家审核和比较实验。

在这些机制和实验完成前，生产路径应称为 `Graph Authoring Agent Workflow`。EDGA 的质量、成本和下游收益只能作为假设。

## 10. 可验证的下一步改进

后续工作应写成测试，而不是默认有效的升级：

1. 比较零重叠与小范围边界重叠，测量 duplicate rate、recall、成本和 reconciliation burden。
2. 对 node-definition/excerpt 样本开展盲法 semantic-support 判断。
3. 在匹配预算下比较 same-model、cross-model 与 human verification。
4. 构建锁定的 expert reference subset，估计 node、edge 和 missing-concept recall。
5. 单独评估 L0-L5 rubric 的专家一致性和回答层级可分性。
6. 在 promotion 前要求 edit-level provenance 或显式 review annotation。
7. 测量 graph variant 对审核成本、simulator fidelity、重建分数和 tested-agent ranking 的影响。

## 11. 实现映射

- 编排：[`workflow.py`](../../../../backend/knowact/authoring/workflow.py)
- Agent steps 与 batching：[`steps.py`](../../../../backend/knowact/authoring/steps.py)
- 确定性切分：[`segments.py`](../../../../backend/knowact/authoring/segments.py)
- Authoring 校验：[`validation.py`](../../../../backend/knowact/authoring/validation.py)
- Candidate artifacts：[`output.py`](../../../../backend/knowact/authoring/output.py)
- Source contract：[`source_configuration.py`](../../../../backend/knowact/authoring/source_configuration.py)
- Source integrity：[`source_material_catalog.py`](../../../../backend/knowact/storage/source_material_catalog.py)
- Promotion：[`review_promotion.py`](../../../../backend/knowact/authoring/review_promotion.py)
- Reviewed storage：[`reviewed_graphs.py`](../../../../backend/knowact/storage/reviewed_graphs.py)
- 运行流程：[`01-graph-authoring.md`](../../../workflow/01-graph-authoring.md)
- 审核与 promotion：[`02-graph-review-promotion.md`](../../../workflow/02-graph-review-promotion.md)
- 研究依据：[`method_map.md`](../04_maps/method_map.md) 与 [`gap_map.md`](../04_maps/gap_map.md)
- 专家审核实验：[`experiments/01_kg_scientific_validity`](../../../../experiments/01_kg_scientific_validity/README.zh-CN.md)

## 12. 最终主张边界

当前方法能够把固定 scope 的来源转化为可复现、可审计的 candidate diagnostic graph，并在人工显式操作后发布为不可覆盖的 reviewed graph version。

它尚不能证明图谱语义完整、具备心理测量效度或优于其他 authoring method。这些仍是实验问题。
