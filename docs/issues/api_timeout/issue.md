## Title

使用 MinerU 将 PDF 解析为 Markdown，并用 Markdown 驱动 graph authoring workflow

## Background

当前 graph authoring API 会读取本地教材 PDF，并通过 OpenAI Responses API 的 base64 `input_file` 形式把完整 PDF 放入模型请求。issue #4 原本计划改成 OpenAI Files API 上传 PDF、获取 `file_id`、再用 `file_id` 调用模型。

这个方向现在需要调整：

1. 直接把 PDF base64 放入 LLM 请求已经导致 response timeout；
2. 当前使用的第三方远端 LLM API 中转站不支持 OpenAI Files API / `file_id` 路径；
3. graph authoring 的核心需求是抽取教材知识点，不需要在 v1 依赖多模态图像理解；
4. Markdown 文本可以本地缓存并反复复用，更适合当前 API 通道。

因此本 issue 的目标改为：**删除 PDF file upload / PDF input_file 路线，改为由 MinerU 将 PDF 解析成同目录 Markdown，再把 Markdown 文本作为 source material 拼入 graph authoring prompt。**

后续验证发现 MinerU 的正式 v4 URL 提交流程不接收 base64 payload，也不要求 KnowAct 把本地 PDF 直接交给 LLM；它需要一个 MinerU 服务可拉取的公网 URL。因此 source preparation 需要新增一个临时公网入口：把本地 PDF 上传到私有阿里云 OSS bucket，生成短期 signed URL，将该 URL 提交给 MinerU v4，再下载 MinerU 结果并缓存 Markdown。

## Problem

当前或原计划流程类似：

```text
Frontend / Backend
  -> local PDF
  -> PDF base64 input_file or OpenAI file_id
  -> LLM 读取 PDF + 执行 graph authoring
  -> 同步等待完整结果
```

问题是：

- PDF base64 请求体过大，容易触发远端 LLM response timeout；
- OpenAI Files API / `file_id` 在当前第三方中转站不可用；
- 保留 PDF-specific LLM client 会让系统出现两条互相竞争的 source input path；
- 每次运行都重新处理 PDF，不利于复用 source material；
- 图像视觉内容不是 v1 source-grounded candidate graph authoring 的必要输入。

## Goal

将流程改为：

```text
POST /api/authoring/graph-candidates
  -> 接收 storage/ 下的 pdf_path
  -> 查找同目录、同 stem 的 .md
  -> 如果 .md 不存在，将 PDF 临时上传到私有 OSS 并生成 signed URL
  -> 如果 PDF 超过 MinerU 单任务页数限制，先拆成不超过 200 页的 PDF chunks
  -> 将每个 PDF 或 PDF chunk 的 signed URL 提交给 MinerU v4 URL extract API
  -> 下载 MinerU result zip，抽取 Markdown；多 chunk 时按原页码顺序拼接
  -> 将拼接后的 Markdown 写出 .md
  -> 如果 force_reparse=true，重新执行 OSS -> MinerU URL 提交流程并覆盖 .md
  -> 读取 Markdown 作为 Parsed Source Markdown
  -> 将 Markdown 放入 SourceMaterial.text
  -> 使用普通 text ModelClient 调用 graph authoring workflow
  -> 写出 candidate_nodes.json、candidate_edges.json 和 workflow_log.json
```

核心目标：

- 不再把完整 PDF base64 放入 LLM 请求；
- 不依赖 OpenAI Files API、`file_id` 或支持 file input 的模型通道；
- 不把 bucket 设为 public-read，只通过短期 signed URL 让 MinerU 拉取一次 source PDF；
- 支持大于 MinerU 单任务页数上限的 PDF，通过本地拆分、逐块解析、Markdown 拼接绕过上限；
- 保留一个统一的 authoring API 入口，方便后续前端接入；
- 通过同目录 Markdown 缓存减少重复解析；
- 保持当前 `Graph Authoring Agent Workflow` 的三步结构；
- 输出仍然是 reviewable candidate graph artifacts，不自动 promote 为 reviewed graph data。

## Non-goals

本 issue 暂时不做：

- OpenAI Files API / `file_id`；
- PDF base64 `input_file`；
- 视觉图像理解；
- RAG 检索；
- embedding；
- 向量数据库；
- section-level map-reduce；
- PDF hash / mtime 自动缓存失效；
- 长期公网 source material 托管；
- OSS source catalog；
- 自动 OSS lifecycle 规则管理；
- 自动 graph promotion。

如果 Markdown 超过模型或中转站 context 限制，先通过人工选择较小 source 或预处理 Markdown 解决；chunking / chapter selection 另开后续 issue。

## Proposed Solution

### 1. 保留统一 authoring API 入口

继续使用：

```text
POST /api/authoring/graph-candidates
```

请求仍以 `pdf_path` 作为主入口，因为 benchmark author 和前端关心的原始材料仍是教材 PDF。

新增请求参数：

```text
force_reparse: bool = false
```

推荐请求示例：

```json
{
  "pdf_path": "books/isl_python.pdf",
  "run_id": "dev_run_001",
  "force_reparse": false
}
```

### 2. 使用 same-directory same-stem Markdown 缓存

Markdown 路径由 PDF 路径自动派生：

```text
storage/books/isl_python.pdf
storage/books/isl_python.md
```

缓存规则：

```text
if .md exists and force_reparse=false:
    use existing .md
if .md missing:
    call MinerU and write .md
if .md exists and force_reparse=true:
    call MinerU, overwrite .md
```

API response 应返回：

```text
markdown_storage_uri
markdown_cache_status: hit | generated | regenerated
```

### 3. 将 MinerU/source preparation 放在 authoring 边界

新增：

```text
backend/knowact/authoring/sources.py
```

建议结构：

```python
class SourceParser(Protocol):
    def parse_pdf_to_markdown(
        self,
        *,
        pdf_path: Path,
        run_id: str | None = None,
        storage_uri: str | None = None,
    ) -> str:
        ...
```

生产实现：

```text
MinerUHTTPSourceParser
AliyunOSSSourceURLPublisher
```

测试实现：

```text
FakeSourceParser
ExistingMarkdownSourceParser
FakeSourceURLPublisher
```

核心 helper：

```text
resolve_or_create_parsed_markdown(...)
```

MinerU 与 OSS signed URL 发布都是 source material preparation，不属于 `backend/knowact/llm/` 的 model completion boundary。

### 3a. 使用私有阿里云 OSS 临时中转 PDF

新增一个小抽象：

```python
class SourceURLPublisher(Protocol):
    def publish_pdf(
        self,
        *,
        pdf_path: Path,
        run_id: str | None = None,
        storage_uri: str | None = None,
    ) -> PublishedSourceURL:
        ...
```

生产实现使用阿里云 OSS Python SDK：

```text
local storage PDF
  -> private OSS bucket object
  -> short-lived signed GET URL
  -> MinerU v4 extract/task
  -> best-effort delete OSS staging object
```

规则：

- bucket 必须保持私有，不使用 public-read；
- signed URL 默认有效期为 `3600` 秒；
- `signed_url_ttl_seconds` 必须大于 `KNOWACT_MINERU_MAX_WAIT_SECONDS + 60`，否则配置错误；
- object key 使用半可读、run-scoped、随机后缀，例如 `knowact/mineru-staging/{run_id}/books/isl_python-{uuid}.pdf`；
- OSS object 是临时中转文件，不是 Source Material Catalog，也不是 reviewed benchmark data；
- 默认在 `finally` 中 best-effort 删除 object；
- `KNOWACT_OSS_KEEP_STAGING_OBJECTS=true` 时保留 object 便于排查；
- API response、workflow log 和错误信息不记录 signed URL；最多记录非敏感 object key 或 redacted staging note。

需要新增环境变量：

```text
ALIYUN_OSS_ENDPOINT=
ALIYUN_OSS_BUCKET=
ALIYUN_OSS_ACCESS_KEY_ID=
ALIYUN_OSS_ACCESS_KEY_SECRET=
KNOWACT_OSS_OBJECT_PREFIX=knowact/mineru-staging
KNOWACT_OSS_SIGNED_URL_TTL_SECONDS=3600
KNOWACT_OSS_KEEP_STAGING_OBJECTS=false
```

### 3b. MinerU standard 模式改为 URL 提交

`KNOWACT_MINERU_API_MODE=standard` 使用 MinerU v4 single-file URL extract API：

```text
POST {KNOWACT_MINERU_API_BASE_URL}/extract/task
  body:
    url: <OSS signed URL>
    model_version: <KNOWACT_MINERU_MODEL_VERSION>
    language: <KNOWACT_MINERU_LANGUAGE>
    enable_table: <KNOWACT_MINERU_ENABLE_TABLE>
    is_ocr: <KNOWACT_MINERU_IS_OCR>
    enable_formula: <KNOWACT_MINERU_ENABLE_FORMULA>
    page_range: <KNOWACT_MINERU_PAGE_RANGE, optional>

GET {KNOWACT_MINERU_API_BASE_URL}/extract/task/{task_id}
  poll until state=done
  download full_zip_url
  extract full.md, falling back to the first .md file
```

`standard` 模式不再使用 `/file-urls/batch` 让 MinerU 生成上传 URL，也不再由 KnowAct 对 MinerU 返回的 URL 执行 `PUT`。

### 3c. 大 PDF 按 MinerU 页数上限拆分

MinerU 当前单个 PDF 任务最多处理 200 页。`MinerUHTTPSourceParser` 在 standard mode 中应先检查 PDF 页数：

```text
if page_count <= KNOWACT_MINERU_MAX_PAGES_PER_TASK:
    submit one OSS signed URL to MinerU
else:
    split PDF into chunks of at most KNOWACT_MINERU_MAX_PAGES_PER_TASK pages
    submit each chunk through OSS signed URL -> MinerU
    download each Markdown result
    concatenate chunk Markdown in original page order
    write the concatenated Parsed Source Markdown cache
```

配置：

```text
KNOWACT_MINERU_MAX_PAGES_PER_TASK=200
```

拼接后的 Markdown 应保留轻量 chunk marker，例如：

```text
<!-- MinerU parsed PDF chunk 1/4: source pages 1-200 -->
```

这些 marker 只是 source preparation provenance，帮助 benchmark author 和 LLM prompt 看到 chunk/page boundary；它们不是 `Source Locator` schema，也不是 reviewed benchmark data。

`KNOWACT_MINERU_PAGE_RANGE` 暂不与自动拆分同时支持；如果设置了 page range 且 PDF 仍需拆分，应直接报配置错误，避免把全局 page range 错误套到每个 chunk。

### 4. Graph authoring workflow 使用 Markdown text

API 层构造 `SourceMaterial` 时，应把 Markdown 内容放入：

```python
SourceMaterial(
    source_id=...,
    title=...,
    citation=...,
    text=markdown_text,
)
```

三个 graph authoring step 暂时都使用完整 Markdown source context：

- `Node Extraction Agent Step`
- `Node Rubric Authoring Agent Step`
- `Edge Proposal Agent Step`

本 issue 不引入 LLM prompt chunking、RAG 或 map-reduce；PDF chunking 只发生在 MinerU source preparation 边界，用于满足 MinerU 单任务页数限制。

### 5. 删除旧 PDF-specific LLM path

删除或停止使用：

```text
backend/knowact/llm/openai_responses_client.py
PDFModelClient
OpenAIResponsesPDFClient
build_openai_pdf_graph_authoring_workflow
base64 input_file tests
```

authoring workflow 应回到普通 `ModelClient.complete(messages=...)` 文本调用路径。

### 6. 图像与图表边界

v1 不把图片文件或视觉内容发送给 LLM。

但 MinerU Markdown 中已有的文本线索应保留：

- headings；
- paragraphs；
- formulas；
- tables；
- figure captions；
- list items。

如果某个知识点只能通过图片视觉内容判断，模型应标记 source detail insufficient 或跳过，不应编造。

### 7. 错误边界

失败时应区分：

```text
pdf_not_found
pdf_invalid
oss_config_invalid
oss_publish_failed
oss_delete_failed_warning
mineru_parse_failed
markdown_empty
markdown_write_failed
llm_generation_failed
authoring_output_parse_failed
validation_failed
```

普通 unit tests 使用 fake parser，不调用真实 MinerU API 或真实 LLM API。
普通 unit tests 也使用 fake URL publisher，不调用真实阿里云 OSS。

## Tasks

- [x] 更新 `GraphCandidateAuthoringRequest`，新增 `force_reparse`。
- [x] 新增 `backend/knowact/authoring/sources.py`。
- [x] 定义 `SourceParser` protocol。
- [x] 实现 `resolve_or_create_parsed_markdown(...)`。
- [x] 实现 same-directory same-stem `.md` path 规则。
- [x] 实现 `markdown_cache_status: hit | generated | regenerated`。
- [x] 新增 MinerU API parser 实现，并从环境变量读取配置。
- [x] 新增 `SourceURLPublisher` / `PublishedSourceURL` 抽象。
- [x] 新增 Aliyun OSS signed URL publisher，并从环境变量读取 OSS 配置。
- [x] 将 `standard` MinerU parser 从 `/file-urls/batch` 上传 URL 流程改为 `/extract/task` URL 提交流程。
- [x] 校验 OSS signed URL TTL 大于 MinerU max wait 加 60 秒。
- [x] 默认 best-effort 删除 OSS staging object，并支持 `KNOWACT_OSS_KEEP_STAGING_OBJECTS=true` 调试保留。
- [x] 新增 PDF 页数检查，超过 `KNOWACT_MINERU_MAX_PAGES_PER_TASK` 时拆分为多个 PDF chunks。
- [x] 逐个 chunk 上传 OSS、提交 MinerU、下载 Markdown，并按原始页码顺序拼接。
- [x] 将 `/api/authoring/graph-candidates` 改为先 resolve/create Markdown，再构造 `SourceMaterial.text`。
- [x] 删除 `OpenAIResponsesPDFClient`。
- [x] 删除 `PDFModelClient` protocol。
- [x] 删除 `build_openai_pdf_graph_authoring_workflow`。
- [x] 将相关 tests 从 PDF base64 input 改成 Markdown cache hit/generated。
- [x] 确认 LLM 请求中不再包含 `data:application/pdf;base64`。
- [x] 更新 README / V1 architecture / V1 breakdown 中的 PDF input_file 描述。
- [x] 更新 README / V1 architecture / V1 breakdown 中的 OSS signed URL source preparation 描述。
- [x] 新增 ADR：V1 graph authoring uses private OSS staging URLs for MinerU.

## Acceptance Criteria

完成后应满足：

1. `POST /api/authoring/graph-candidates` 仍以 `pdf_path` 作为统一入口；
2. 若同目录同 stem `.md` 已存在且 `force_reparse=false`，API 复用该 Markdown；
3. 若 `.md` 不存在，API 调用 MinerU 解析 PDF 并保存 Markdown；
4. 若 `force_reparse=true`，API 重新解析并覆盖 Markdown；
5. Graph authoring workflow 的 LLM 输入是 Markdown text，而不是 PDF base64、OpenAI `file_id` 或 `input_file`；
6. MinerU `standard` mode 通过私有 OSS bucket 的短期 signed URL 调用 `/extract/task`，不依赖 public-read bucket；
7. signed URL 默认有效期为 3600 秒，且必须长于 MinerU max wait；
8. OSS staging object 默认 best-effort 删除，调试开关可保留；
9. 大于 `KNOWACT_MINERU_MAX_PAGES_PER_TASK` 页的 PDF 会被拆分、逐块解析并拼接成一个 cached Parsed Source Markdown；
10. 旧 PDF-specific LLM client path 被删除；
11. API response 返回 Markdown URI 和 cache status；
12. API response、workflow log 和错误信息不泄漏 OSS signed URL；
13. unit tests 不调用真实 MinerU、真实 OSS 或真实 LLM；
14. candidate graph final output 仍然只有 `candidate_nodes.json` 和 `candidate_edges.json`，`workflow_log.json` 仍是 sidecar artifact；
15. 该 API 不 promote reviewed authored graph data。

## Notes

本 issue 的重点不是把 PDF 上传给模型，而是把：

```text
PDF -> LLM file input
```

改成：

```text
PDF -> MinerU -> cached Markdown -> LLM text prompt
```

这样可以绕开当前远端 LLM 通道不支持 file upload 的限制，并降低 PDF 直传带来的 response timeout 风险。

引入 OSS 后，更精确的 source preparation 路线是：

```text
local PDF
  -> private Aliyun OSS staging object
  -> short-lived signed URL
  -> MinerU v4 URL extract
  -> result zip / Markdown
  -> cached Parsed Source Markdown
  -> LLM text prompt
```

对于大于 200 页的 PDF，`local PDF` 和 `private Aliyun OSS staging object` 之间会多一步本地 PDF chunking；每个 chunk 独立走 OSS signed URL 和 MinerU v4 URL extract，最后再拼接为一个 cached Parsed Source Markdown。
