# KnowAct

[English](README.md)

**KnowAct：在知识驱动的人机交互中评估功能性心智理论能力**

KnowAct 是一个面向研究的基准与评估框架，用于研究 AI agent 如何在知识驱动的人机交互中使用类似心智理论（Theory of Mind, ToM）的能力。

KnowAct 关注的不是模型能否描述用户的心理状态，而是一个更偏功能性的问题：

> agent 能否利用它对用户的建模，做出更好的交互决策？

本项目探索 agent 如何在多轮交互中推断、更新并利用用户的知识状态。

---

## 研究动机

大语言模型 agent 正越来越多地参与学习、研究、写作和决策等开放式协作任务。在这些场景中，一个有用的 agent 不仅需要理解外部任务，也需要推理用户的内部状态：

- 用户已经知道什么？
- 用户缺少或误解了哪些概念？
- agent 接下来应该问什么？
- agent 什么时候应该解释、质疑、总结或推进任务？
- agent 应该如何根据用户的知识画像调整行为？

这种能力与 **心智理论** 有关，但 KnowAct 更强调它在交互中的实际作用。我们将这一方向称为 **功能性心智理论**：使用用户状态推理来指导对话行动的能力。

---

## 核心研究问题

KnowAct 研究的问题是：

> 如何评估一个 AI agent 是否能使用类似心智理论的用户建模能力，来指导知识驱动任务中的交互决策？

更具体地说，本项目关注：

1. agent 能否通过有限交互推断用户隐藏的知识画像？
2. agent 能否基于推断出的画像选择有用的对话行动？
3. 我们能否定量比较 agent 重建出的用户画像与真实画像？
4. 具备 ToM 意识的 agent 循环，是否能在画像重建和交互质量上优于更简单的基线方法？

---

## 核心思路

KnowAct 构造受控的用户画像，并测试 agent 能否通过对话恢复并使用这些画像。

基本评估流程如下：

```text
真实知识画像
        ↓
用户模拟器
        ↓
多轮交互
        ↓
被测 agent 推断用户画像
        ↓
画像比较 / 评分
```

真实用户画像对被测 agent 隐藏。agent 必须与模拟用户交互、提出问题、解释用户回答，并逐步重建用户的知识状态。

---

## 基准设计

KnowAct 使用半合成的基准构造流程：

v1 先从单一 benchmark domain `classical_supervised_ml_algorithms` 开始，用于跑通 data authoring、simulation、active diagnosis、final reconstruction 和 scoring，再考虑跨领域校准。第一版 graph 目标规模为 30-50 个 knowledge nodes，并以 *An Introduction to Statistical Learning with Applications in Python* 为 source grounding；这足够区分不同用户知识结构，同时保持 authoring 和审核可控。第一版暂不纳入 deep learning、reinforcement learning 和 unsupervised learning。

1. **Benchmark 数据编写**

   项目自写的 graph authoring agent workflow 会通过模型 API 调用生成 candidate knowledge graph 和 candidate knowledge map。其中一个 step 读取 Parsed Source Markdown，并抽取带 source locator 和简短 source grounding notes 的 source-grounded node skeleton；后续 node rubric 与 edge proposal steps 只消费这些结构化 intermediate artifacts，不再接收完整 source text。node rubric step 补全 diagnostic goal、L0-L5 rubrics、diagnostic signals 和 simulator behavior；edge step 使用完整 candidate nodes、rubrics、locators 和 source grounding notes 提议 candidate edges。graph authoring workflow 的最终审阅输出是两个 JSON list 文件，分别存放 nodes 和 edges；candidate 状态只属于文件名或审阅状态，不写进 node / edge 对象内容。人工 review 后，authored graph data 也继续分成 node 与 edge 两个 JSON list 文件存储。Candidate nodes 必须从选定 authoritative source 中抽取，并保留 source locator；不应依赖模型记忆现场编写。Persona、background、preferences 和 task goal 可以指导 map 生成，但 v1 evaluation 的评分只使用 benchmark author 审核后的 authored knowledge graph 和 ground-truth knowledge map。

   每个 v1 evaluation episode 由显式 manifest 声明，用于绑定 authored graph、hidden map、可选 profile context、`max_turns`、interaction rule 和固定的 `squared_mastery_distance_v1` scoring profile。

2. **人工校验**

   人工检查并修订生成的画像，确保其一致性、可信度和可评估性。

3. **用户模拟**

   基于隐藏知识地图和 evidence 构造 LLM 用户模拟器，使其自然回答诊断问题，但不暴露 mastery label、hidden evidence id 或完整真实知识地图。它可以表现出不确定、部分正确或误解，但回答应与隐藏 map 和 evidence 保持一致。

4. **agent 交互**

   被测 agent 在无法访问隐藏画像的情况下与模拟用户交互。

5. **画像重建**

   对话结束后，被测 agent 提交最终重建知识地图。每轮 reconstruction trace 可以作为可选分析产物保留。

6. **评估**

   使用结构化 map comparison，将最终重建知识地图与隐藏真实知识地图进行比较。

---

## 知识图谱与知识地图

KnowAct 区分用户无关的 **知识图谱** 与用户相关的 **知识地图**。

**知识图谱** 表示稳定的领域知识结构：

- `nodes`：可诊断的知识单位。
- `edges`：node 之间的客观关系。

**知识地图** 表示某个用户或被测 agent 在这张图谱上的知识状态。用户状态只维护 node-level state；edge 用于探索和诊断路径，不用于描述用户状态。

一个可能的图谱结构如下：

```json
{
  "nodes": [
    {
      "id": "epistemic_uncertainty",
      "name": "Epistemic Uncertainty",
      "type": "concept"
    },
    {
      "id": "active_learning",
      "name": "Active Learning",
      "type": "concept"
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

一个可能的用户知识地图结构如下：

```json
{
  "user_id": "u_001",
  "userstate": [
    {
      "node_id": "active_learning",
      "mastery_level": "L2",
      "evidence_refs": ["ev_104"],
      "misconceptions": [],
      "unknowns": []
    }
  ]
}
```

知识图谱与知识地图既可以支持评估，也可以支持 agent 的决策过程。

---

## 评估维度

KnowAct v1 将评估重点放在隐藏的真实知识地图与被测 agent 重建出的知识地图之间的自动比较。

### 1. 画像重建准确率

将 agent 重建出的知识地图与真实知识地图中的结构化用户状态字段进行比较。v1 的主结果是 `episode_mastery_distance`：episode 使用的 authored knowledge graph 中所有 nodes 的预测 `mastery_level` 与隐藏参考之间的平均平方距离。越低越好。

可能的辅助指标包括：

- 误解检测准确率
- missing prediction 比例
- unsupported inference 比例，即缺少可见 evidence 引用的推断比例

v1 的主评分不引入额外 evaluator agent 或 LLM judge。Evidence record 的作用是让重建更有依据、更可审计，而不是增加另一层主观评价。Unsupported inference 与 mastery-level distance 分开报告。

### 2. 交互效率

agent 应该在显式 turn budget 内恢复有用信息。v1 的 episode 直接配置 `max_turns`，不根据 graph node 数量自动推导。一个 turn 包含一个主要诊断问题和一个 simulator answer。

可能的指标包括：

- 使用的对话轮数
- 每轮信息增益
- 冗余问题比例
- 重要画像维度覆盖率
- 早期阶段的重建质量

### 3. 行动质量

后续版本可以评估 agent 是否使用推断出的画像做出更好的教学或推荐决策。v1 中，交互先限制为主动知识状态诊断。

v1 的主要行动类型是：

- 提出诊断性问题

目标是在有限轮次内高效推断用户状态，并产出有 evidence 支撑的重建结果。

---

## Agent 循环

KnowAct 计划包含一个具备 ToM 意识的 agent 循环。

简化版本如下：

```text
观察用户回答
        ↓
更新推断出的知识地图
        ↓
估计不确定性
        ↓
选择下一步交互行动
        ↓
生成回复
        ↓
继续交互
```

该 agent 循环显式区分：

- 用户状态推断
- 不确定性估计
- 行动选择
- 回复生成
- 画像重建

这使得我们可以比较不同 agent 设计，并分析失败发生在哪个环节。

---

## 基线方法

KnowAct 旨在比较具备 ToM 意识的 agent 与更简单的基线方法，例如：

### 直接聊天基线

v1 暂不纳入。主动诊断 loop 稳定后可以再考虑。

### 被动总结基线

v1 暂不纳入。被动重建后续可能有价值，但 v1 先关注诊断问题选择。

### 固定问题基线

agent 遵循预设诊断问题顺序，不根据先前回答调整问题。

### 随机问题基线

agent 在 episode 约束内随机选择诊断问题。

### Simple LLM Agent

agent 可以看到 authored knowledge graph 和对话历史，用简单 prompt 选择下一轮诊断问题，并提交最终重建知识地图。

### 真实画像基线

v1 暂不纳入。Oracle 后续可作为上限参考，但不是跑通第一版 benchmark loop 的必要条件。

---

## 研究假设

KnowAct 基于以下假设：

> 具备显式用户建模和类 ToM 行动选择能力的 agent，应该比缺少这些机制的 agent 更准确地推断用户知识状态，并更高效地进行交互。

本项目将在受控的知识驱动交互环境中检验这一假设。

---

## 当前状态

KnowAct 目前处于设计和原型阶段。

V1 实现已经从 schema 与 validation spine 开始：

- `backend/knowact/core/`：知识图谱、evidence record、知识地图、episode manifest 和 scoring report 的 Pydantic schema。
- `backend/knowact/validation/`：用于 graph 引用、map coverage/evidence support 和 episode manifest 约束的跨对象 validator。
- `backend/knowact/authoring/`：Phase 2 graph authoring workflow spine，包含 node extraction、node rubric authoring、edge proposal、candidate file export 边界，以及分离的 `templates/` 和 `parsers/` 模块来管理 agent prompts 与 raw model outputs。
- `backend/knowact/llm/`：model-client interface，以及基于 OpenAI 和 DeepSeek SDK 的 clients，用于 text-based authoring steps。
- `backend/knowact/storage/`：local artifact、material path 与 reviewed graph/map promotion helpers。测试阶段的书本 PDF 可以放在仓库根目录的 `storage/` 下；该目录除 `.gitkeep` 外默认被 git 忽略。
- `backend/knowact/api/` 与 `backend/main.py`：FastAPI 入口，以及可从本地教材 PDF 运行真实 graph authoring workflow 的 authoring API。
- `frontend/`：React/Vite research workbench，包含顶层 Knowledge Graph 与 User Profile 模块。它支持 candidate graph review，以及 Profile Context generation、编辑、保存与不可变 confirmation gate。
- `benchmark/fixtures/dev_classical_supervised_ml_algorithms/`：用于 schema 与 validator 检查的 5-node development fixture，不是正式的 30-50 node v1 graph。
- `test/`：覆盖公开 schema 与 validation API 的 `unittest` 测试。

本地 OpenAI API 配置可以复制 `.env.example` 为 `.env`，并填写：

```bash
OPENAI_API_KEY=...
KNOWACT_OPENAI_MODEL=gpt-4.1-mini
```

DeepSeek 可以在单次 authoring 请求中通过 `client_provider="deepseek"` 选择，API key 与模型默认值通过环境变量配置，不放入 request body：

```bash
DEEPSEEK_API_KEY=...
KNOWACT_DEEPSEEK_MODEL=deepseek-v4-flash
KNOWACT_DEEPSEEK_BASE_URL=https://api.deepseek.com
KNOWACT_DEEPSEEK_TIMEOUT_SECONDS=120
```

当前测试使用 deterministic fixtures 和 fake clients，不会调用 OpenAI 或 DeepSeek API。

当前 Python 检查命令：

```bash
uv run python -m unittest
```

手动验证阿里云 OSS signed URL 上传和公网访问：

```bash
uv run python scripts/manual_aliyun_oss_smoke.py
```

启动后端开发 API：

```bash
uv run fastapi dev backend/main.py
```

在第二个终端启动前端 workbench：

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

运行 Candidate Graph Review Workbench model 检查：

```bash
npm --prefix frontend run test:candidate-graph-workbench
```

如果后端运行在非默认端口，可以设置 `VITE_API_PROXY_TARGET`，例如：

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8001 npm --prefix frontend run dev
```

然后打开 Vite 输出的前端地址，或打开本地 Swagger UI：`http://127.0.0.1:8000/docs`。当前 authoring API 包含：

- `POST /api/authoring/source-materials` 和 `GET /api/authoring/source-materials`：把 PDF source material 上传到 `storage/source_materials/{source_id}/original.pdf`，写出 `metadata.json`，并为 workbench 列出已登记 source materials。
- `GET /api/authoring/benchmark-domains`：为 workbench selector 列出现有 benchmark-domain 目录，不创建或修改 benchmark data。
- `POST /api/authoring/graph-candidates`：按 `storage/` 下的相对路径读取一个 PDF，解析或复用同目录同 stem 的 Parsed Source Markdown，必要时调用 MinerU 创建或重新生成 Markdown，再只把 Markdown 文本发送给 node extraction step，返回 source-grounded skeletons、candidate nodes、candidate edges、Markdown cache metadata 和 compact run log summary，并默认写出 `candidate_nodes.json`、`candidate_edges.json`、通过 validation 的 `intermediate/` artifacts 以及 sidecar `workflow_log.json`。workflow log 记录 step 状态，并链接到 `agent_traces/{step}/model_raw_output.txt`、`agent_traces/{step}/parser_output.json` 和适用时的 batch trace artifacts 以便 debug，但仍不写入完整 prompt/source-material text。MinerU standard mode 会先把本地 PDF 发布为私有阿里云 OSS staging object 的短期 signed URL，再把这个 URL 提交给 MinerU；超过 `KNOWACT_MINERU_MAX_PAGES_PER_TASK` 的 PDF 会拆成 chunks 并按页码顺序拼接 Markdown。其中只有 node 和 edge 文件是 candidate graph review artifacts。示例请求：
- `GET /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}` 和 `PUT /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}`：读取和 validate-save candidate graph review artifacts。保存端点只有在 schema 与 graph validation 通过后，才会覆盖 `candidate_nodes.json` 和 `candidate_edges.json`。
- `POST /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}/promotion`：重新校验已保存的 candidate artifacts，将它们复制到 `benchmark/domains/{benchmark_domain}/graphs/{version}/` 下并命名为 `authored_nodes.json` 与 `authored_edges.json`，同时生成 `graph_manifest.json`。Reviewed graph version 不可变：已有 version 返回 `409 Conflict`，修订必须发布新的 version。
- `POST /api/authoring/profile-context-candidates`：生成一份可 review 的 synthetic-user Profile Context 草稿，并写出最小 candidate run artifacts。
- `GET /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}` 和 `PUT /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}`：读取和 validate-save 当前 Profile Context 草稿。保存端点只编辑 persona 字段；run identity 与 benchmark domain 保持固定。
- `POST /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}/confirmation`：把一份已校验草稿发布为不可变的 `benchmark/domains/{benchmark_domain}/users/{user_id}/profile_context.json`。Confirmed user id 不允许覆盖，每个 candidate run 最多 confirmation 一次。
- `POST /api/authoring/map-candidates`：按 identity 加载一个 reviewed graph version 与一个 confirmed Profile Context，运行一次 full-graph knowledge-state outline 调用，将 evidence authoring 按 reviewed-node 连续窗口分批，并写出 `candidate_map.json`、`consistency_warnings.json`、`workflow_log.json`、outline/evidence intermediates 和逐批 step traces。Evidence batch 默认包含 `5` 个 nodes，并接受可选的正整数 `evidence_batch_size` override。可选的 `sampling_temperature` 默认值为 `0.7`，同一个值用于 outline 调用和每个 evidence batch。Candidate-map run id 不允许覆盖已有 run；重试必须使用新的 run id。
- `GET /api/authoring/candidate-maps/{benchmark_domain}/{run_id}`：返回一份已保存的 Candidate Knowledge Map 及其 artifact references，供检查使用。
- `POST /api/authoring/candidate-maps/{benchmark_domain}/{run_id}/promotion`：用 reviewed graph 与 confirmed Profile Context 重新校验一份已保存的 Candidate Knowledge Map，将 `kind` 转换为 `ground_truth`，并发布不可变的 `ground_truth_maps/{map_id}/ground_truth_map.json` 与 `map_manifest.json`。已有 `map_id` 返回 `409 Conflict`，同一个 candidate run 最多 promotion 一次，generation-time `consistency_warnings.json` 不会复制到 reviewed data。

```json
{
  "pdf_path": "books/isl_python.pdf",
  "client_provider": "openai",
  "run_id": "dev_run_001",
  "force_reparse": false
}
```

PDF source material 请求被限制在 `storage/` 内，拒绝绝对路径和 `..` 路径穿越。对于 `storage/books/isl_python.pdf`，默认 Markdown 缓存路径是 `storage/books/isl_python.md`；除非 `force_reparse=true`，已有 Markdown 会被复用。LLM 路径使用 Markdown text，不使用 PDF base64 `input_file` 或 OpenAI `file_id`；`client_provider` 当前接受 `openai` 或 `deepseek`，默认值为 `openai`。OSS staging object 只是 MinerU URL parsing 的私有临时传输层；signed URL 不会出现在 API response 或 workflow log 中。Candidate generation 不会自动 promotion；reviewed graph 与 ground-truth map publication 都是独立的显式 promotion 操作。

已实现或计划中的组件包括：

- [x] V1 core schema 与 validation spine
- [x] 知识地图表示
- [x] Phase 2 graph authoring workflow spine
- [x] OpenAI 与 DeepSeek SDK client boundary for LLM-backed steps
- [x] FastAPI authoring API，用于真实 source-backed graph candidate runs
- [x] Candidate Graph Review Workbench 前端
- [x] Phase 3 review-gated authored graph promotion 与 graph manifest generation
- [x] 基于 LLM 的 Profile Context generation 与不可变 confirmation gate
- [x] Single-batch Candidate Knowledge Map generation tracer bullet
- [x] Reviewed Ground-Truth Knowledge Map promotion 与 map manifest generation
- [ ] Ground-truth map authoring
- [ ] 人工校验协议
- [ ] 用户模拟器
- [ ] 被测 agent 接口
- [ ] ToM-aware agent 循环
- [ ] 基线 agent
- [ ] 结构化 map comparison 指标
- [ ] 评估脚本
- [ ] 实验报告

---

## 示例任务设置

一个可能的基准场景：

```text
领域：研究论文阅读

真实用户画像：
- 理解基础 LLM 概念
- 对 RAG 有部分了解
- 尚未充分理解心智理论
- 混淆用户建模与个性化
- 希望围绕 AI 辅助论文阅读设计研究项目

Agent 目标：
- 与用户交互
- 推断用户知识状态
- 识别缺失概念和误解
- 构建重建出的知识地图
- 选择有帮助的下一步行动
```

agent 将根据其重建画像与隐藏真实画像的接近程度，以及它在对话中使用该画像的有效程度进行评估。

---

## 为什么是 KnowAct？

现有评估通常测试模型是否能回答关于信念、意图或隐藏状态的问题。KnowAct 则关注模型能否在交互中使用这类推理。

本项目将评估重点从：

```text
模型能否描述用户的心理状态？
```

转向：

```text
模型能否因为建模了用户心理状态而行动得更好？
```

因此，KnowAct 尤其适用于教育 agent、研究助手、个性化 AI 系统和知识驱动的协作 agent。

---

## 路线图

未来方向包括：

- 设计更丰富的知识地图结构
- 创建论文阅读之外的多个领域
- 在用户画像中加入受控误解
- 衡量主动信息寻求行为
- 比较不同 agent 架构
- 研究用户模拟中的失败模式
- 降低画像生成、模拟和评估之间的循环依赖
- 在合成验证后使用真实人类用户进行测试

---

## 引用

本项目仍在积极开发中。引用信息将在后续补充。
