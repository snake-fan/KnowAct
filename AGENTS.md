# KnowAct Agent Guide

本文件用于约定 AI coding agents 在 KnowAct 仓库中的工作方式。请优先遵循本文件；当它与用户最新指令冲突时，以用户最新指令为准。

## Project Snapshot

- 项目名：KnowAct
- 项目定位：KnowAct 是一个面向研究的 benchmark 与 evaluation framework，用于评估 AI agents 在知识驱动人机交互中是否能使用功能性心智理论（Functional Theory of Mind）进行用户建模和行动选择。
- 核心目标：通过隐藏的 ground-truth user profile、LLM user simulator、多轮交互、profile reconstruction 与 scoring，评估 agent 是否能推断用户知识状态并据此做出更好的交互决策。
- 主要文档：
  - `README.md`：项目说明。
  - `docs/KnowledgeGraph.md`：知识图谱、知识地图、概念关系和画像结构设计记录。
  - `docs/V1ProjectArchitecture.md`：V1 项目架构、模块边界和推荐目录布局；开发前必须阅读。
  - `docs/V1ProjectBreakdown.md`：V1 阶段拆解、里程碑和实现顺序；开发前必须阅读。
  - `AGENTS.md`：面向 AI agents 的协作约定。

## Tech Stack

- Frontend：React。
- Backend：FastAPI。
- Backend schemas：Pydantic。
- Python 包管理：`uv`。
- Python 版本：以 `.python-version` 和 `pyproject.toml` 为准，当前为 Python 3.12。

## Expected Architecture

仓库仍处于设计和原型阶段。新增结构时应保持清晰边界，建议按以下方向演进：

新增或调整源码结构、模块边界、runtime wiring、schema、validation、authoring、simulator、agent、scoring、reports 或 frontend workbench 前，agent 必须先阅读 `docs/V1ProjectArchitecture.md` 和 `docs/V1ProjectBreakdown.md`。架构实现应跟随 `docs/V1ProjectArchitecture.md` 的推荐模块边界和数据流；开发顺序应参考 `docs/V1ProjectBreakdown.md` 的阶段拆解。不要在未对齐这两份文档的情况下随意新增平行目录、替代概念或临时架构。若这两份文档与已接受 ADR 或 `CONTEXT.md` 冲突，以 ADR 和 `CONTEXT.md` 为准，并在最终回复中说明冲突点。

- `frontend/`：React 前端，用于 benchmark 配置、交互界面、实验结果查看和知识地图可视化。
- `backend/`：FastAPI 后端，用于 profile generation、user simulator、agent loop、evaluation API 和实验任务编排。
- `backend/knowact/api/`：FastAPI routers；当前包含 `/api/authoring` surface，用于从本地教材 PDF 运行真实 graph authoring workflow、生成 reviewable candidate graph artifacts，并通过显式 review confirmation 将校验后的 candidate snapshot promote 为 reviewed authored graph version。
- `backend/knowact/core/` 和 `backend/knowact/validation/`：当前 V1 已开始实现的 schema 与 validation spine。
- `benchmark/fixtures/`：小型 development fixtures，可用于跑通 schema、validation 和 runtime wiring；不要把它们误认为正式 v1 benchmark graph。
- `test/`：当前 Python `unittest` 测试入口。
- `docs/`：研究设计、数据 schema、知识地图、评估指标和实验记录。

如果实际目录结构发生变化，请同步更新 `README.md`、`README.zh-CN.md` 和本文件。

## Domain Concepts

开发时应保持这些概念的边界清晰：

- Ground-truth user profile：隐藏的真实用户知识画像。
- User simulator：基于真实画像进行多轮回答的模拟用户。
- Tested agent：被评估的 agent，不能直接访问真实画像。
- Knowledge graph：用户无关的客观知识结构，由可诊断的 knowledge nodes 和严格限制的 knowledge edges 组成。
- Knowledge map：某个用户或被测 agent 在 knowledge graph 上的知识状态视图，用户状态只维护 node-level state。
- Profile reconstruction：agent 在交互中或交互后重建出的用户画像。
- Evaluation metrics：用于比较真实画像与重建画像，并衡量交互效率和行动质量的指标。

## Working Principles

- 先读上下文，再动手修改。涉及开发或架构决策时，必须先查看 `docs/V1ProjectArchitecture.md` 和 `docs/V1ProjectBreakdown.md`，再阅读 `README.md`、`README.zh-CN.md`、相关 `docs/` 文档和目标文件附近实现。
- 保持改动小而清晰。不要顺手重构无关文件，也不要替用户撤销未明确要求撤销的改动。
- 技术实现应服务于研究问题：用户建模、知识地图、交互行动选择、画像重建和评估。
- v1 设计不追求一次性穷尽所有细节。核心问题和边界大体确定后，优先实现可运行的窄切片，再通过代码、测试和实验结果反复打磨。
- 不要绕开 V1 架构文档自行发明新的模块划分、数据流或业务命名；如确需偏离，应先说明原因，并同步更新相应文档。
- 新增约定、命令、目录或实验流程时，同步更新对应文档。
- 命名应表达业务意图，避免只描述实现细节。

## Frontend Guidelines

- 使用 React 构建前端。
- 优先实现真实可用的研究工作流界面，而不是营销式首页。
- 面向 benchmark / research tooling 的界面应保持清晰、克制、可扫描，适合配置、对比和反复实验。
- 知识图谱 / 知识地图相关 UI 应区分客观 node/edge 结构与用户状态，并突出概念、边、状态、证据和置信度。
- 前端新增启动、构建、测试命令后，必须记录到 README 或本文件。

## Backend Guidelines

- 使用 FastAPI 构建后端 API。
- API 设计应围绕清晰资源与研究流程，例如 profiles、simulations、interactions、agents、evaluations、knowledge-maps。
- 数据模型优先使用 Pydantic schema，保持请求、响应和内部评估对象结构明确。
- 用户画像、知识地图和评估结果应尽量使用结构化数据，不使用脆弱的字符串拼接来表达核心对象。
- LLM 调用、用户模拟、agent loop 和 metric scoring 应保持模块边界，便于替换模型和比较 baseline。

## Repository Conventions

- 默认使用 Markdown 记录设计和决策。
- 英文 README 与中文 README 应互相链接，并保持核心内容同步。
- 文档标题使用英文或中文均可，但同一文件内保持风格一致。
- 代码、命令、路径和配置键使用反引号标记。
- 若新增源码目录，请在 README 中补充项目结构与启动方式。
- 若新增测试体系，请在 README 或本文件中记录测试命令。

## Agent skills

### Issue tracker

Issues and PRDs for this repo are tracked in GitHub Issues for `snake-fan/KnowAct`. See `docs/agents/issue-tracker.md`.

### Triage labels

This repo uses the default five-label triage vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This repo uses a single-context domain documentation layout. See `docs/agents/domain.md`.

## Development Workflow

1. 检查当前工作区状态，识别用户已有改动。
2. 开发前阅读 `docs/V1ProjectArchitecture.md` 和 `docs/V1ProjectBreakdown.md`，确认当前任务对应的模块边界、数据流和阶段目标。
3. 阅读与任务相关的最小上下文，包括目标文件附近实现、README、相关 docs、ADR 或 `CONTEXT.md`。
4. 实施聚焦改动，确保目录、命名和接口与 V1 架构文档保持一致。
5. 运行可用的格式化、类型检查或测试命令。
6. 在最终回复中说明改动内容、验证结果和遗留风险；若偏离 V1 架构文档，必须说明原因和后续文档同步需求。

## Testing And Verification

当前仓库尚未形成完整测试体系。添加前后端代码后，优先建立以下验证入口：

- Current Python schema checks：`uv run python -m unittest`
- Backend：`uv run pytest`
- Backend dev server：`uv run fastapi dev backend/main.py` 或项目实际入口命令
- Frontend：按实际包管理器记录 `npm` / `pnpm` / `bun` 命令

在命令未定义前，agents 应通过阅读变更、检查 Markdown 渲染结构和保持文件一致性来完成基础验证。

## Documentation Notes

- `docs/KnowledgeGraph.md` 应用于沉淀知识地图、概念关系、用户知识状态和画像重建设计。
- `docs/V1ProjectArchitecture.md` 是 V1 源码结构、模块边界、runtime 闭环和 visibility boundary 的主要依据。
- `docs/V1ProjectBreakdown.md` 是 V1 里程碑、开发顺序和窄切片优先级的主要依据。
- README 应保持面向新读者：项目是什么、研究问题是什么、如何运行、如何贡献。
- 重要设计选择应写入文档，而不是只在提交信息或对话里出现。
- 当英文 README 和中文 README 内容发生实质变化时，应尽量同步另一种语言版本。

## Safety Notes For Agents

- 不运行破坏性 git 命令，除非用户明确要求。
- 不删除未跟踪文件，除非用户明确要求。
- 不引入网络依赖或安装包，除非任务确实需要并获得用户许可。
- 不提交密钥、真实用户隐私数据、生产凭据或不可公开的实验数据。
- 对 LLM 生成的用户画像和模拟对话保持可追溯性，避免把模拟数据误标为真实用户数据。
