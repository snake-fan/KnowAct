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

## 本地启动项目

前置要求：

- Python 3.12，与 `.python-version` 保持一致
- 使用 `uv` 管理 Python 依赖
- 使用 Node.js 和 `npm` 运行 React workbench

在仓库根目录安装后端依赖，并准备本地环境变量文件：

```bash
uv sync
test -f .env || cp .env.example .env
```

只有在运行需要外部服务的流程时才需要填写 `.env`，例如 LLM-backed graph authoring、simulator turn、MinerU 解析或阿里云 OSS staging。仅启动后端健康检查和本地 UI/API 联调时，可以先不填真实密钥。

启动 FastAPI 后端：

```bash
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

后端默认监听 `http://127.0.0.1:8000`。开发时常用地址包括 `http://127.0.0.1:8000/health` 和 `http://127.0.0.1:8000/docs`。

另开一个终端，安装并启动前端：

```bash
cd frontend
npm install
npm run dev
```

打开命令输出中的 Vite 地址，通常是 `http://localhost:5173`。Vite dev server 会把 `/api` 和 `/health` 代理到 `http://127.0.0.1:8000`；如果后端运行在其他端口，可以用 `VITE_API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev` 启动前端。

基础验证命令：

```bash
uv run python -m unittest
cd frontend && npm run build
```

---

## 基准设计

KnowAct 使用半合成的基准构造流程：

v1 先从单一 benchmark domain `statistical_learning_with_python` 开始，用于跑通 data authoring、simulation、active diagnosis、final reconstruction 和 scoring，再考虑跨领域校准。当前 V1 graph scope 跟随完整选定 authoritative source，即 *An Introduction to Statistical Learning with Applications in Python*，不再使用早期 supervised-only slice 或固定 30-50 nodes 目标。仍使用旧 `classical_supervised_ml_algorithms` 名称的现有 artifacts 或代码路径应视为 migration / compatibility 状态。

1. **Benchmark 数据编写**

   项目自写的 graph authoring agent workflow 会通过模型 API 调用生成 candidate knowledge graph 和 candidate knowledge map。Graph authoring 先从 Parsed Source Markdown 派生 Parsed Source Segments，再抽取 segment-level node drafts，并通过专门的 reconciliation step 生成带 source locator 和简短 source grounding notes 的 source-grounded node skeleton；后续 node rubric 与 edge proposal steps 只消费这些结构化 intermediate artifacts，不再接收完整 source text。node rubric step 补全 diagnostic goal、L0-L5 rubrics、diagnostic signals 和 simulator behavior；edge step 使用完整 candidate nodes、rubrics、locators 和 source grounding notes 提议 candidate edges。graph authoring workflow 的最终审阅输出是两个 JSON list 文件，分别存放 nodes 和 edges；candidate 状态只属于文件名或审阅状态，不写进 node / edge 对象内容。人工 review 后，authored graph data 也继续分成 node 与 edge 两个 JSON list 文件存储。Candidate nodes 必须从选定 authoritative source 中抽取，并保留 source locator；不应依赖模型记忆现场编写。Persona、background、preferences 和 task goal 可以指导 map 生成，但 v1 evaluation 的评分只使用 benchmark author 审核后的 authored knowledge graph 和 ground-truth knowledge map。

   每个 v1 evaluation episode 由显式 manifest 声明，用于绑定 authored graph、hidden map、可选 profile context、`max_turns`、interaction rule 和固定的 `squared_mastery_distance_v1` scoring profile。

2. **人工校验**

   人工检查并修订生成的画像，确保其一致性、可信度和可评估性。

3. **用户模拟**

   基于隐藏知识地图和 evidence 构造 LLM 用户模拟器，使其自然回答诊断问题，但不暴露 mastery label、hidden evidence id 或完整真实知识地图。它可以表现出不确定、部分正确或误解，但回答应与隐藏 map 和 evidence 保持一致。
   Phase 5 simulator workflow、question grounding、validation、fallback 和 single-turn 边界见 `docs/UserSimulator.md`。

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
  "states": [
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

KnowAct v1 将评估重点放在隐藏的真实知识地图与被测 agent 最终重建提交之间的自动比较。

### 1. 画像重建准确率

被测 agent 提交覆盖全图的最终重建结果，为每个 node 给出一个 `unknown|L0|...|L5` mastery 预测。v1 的主结果是 `episode_mastery_distance`：episode 使用的 authored knowledge graph 中所有 nodes 的预测 `mastery_level` 与隐藏参考之间的平均平方距离。提交的 `unknown` 视为 missing prediction，距离罚分为 `36`。越低越好。

可能的辅助指标包括：

- missing prediction 比例
- unsupported inference 比例，即缺少可见 evidence 引用的推断比例
- exact mastery match 比例
- per-node signed mastery error

v1 的主评分不引入额外 evaluator agent 或 LLM judge。Evidence record 的作用是让重建更有依据、更可审计，而不是增加另一层主观评价。Unsupported inference 与 mastery-level distance 分开报告，misconceptions / unknowns 文本不进入第一版自动评分。

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
