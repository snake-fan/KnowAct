## Title

使用 OpenAI Files API 上传 PDF 并通过 file_id 进行一次性结构化生成

## Background

当前在调用 LLM API 分析 PDF 时，会将较大的 PDF 文件以 base64 编码形式直接放入请求体或 prompt 中，并要求模型一次性完成复杂的结构化生成任务。

这种方式容易导致：

1. 请求体过大；
2. 网络传输时间过长；
3. 服务端处理时间不可控；
4. HTTP 请求容易超时；
5. 同一个 PDF 每次调用都需要重复传输；
6. 复杂分析任务还未完成，接口连接就已经断开。

本 issue 的目标是：**将 PDF 从 base64 直传模型请求，改为先上传到 OpenAI Files API 获取 file_id，再基于 file_id 进行一次性结构化数据生成。**

## Problem

当前流程类似：

```text
Frontend / Backend
  -> PDF base64
  -> 直接放入 LLM 请求
  -> LLM 解析 PDF + 执行复杂任务
  -> 同步等待完整结果
```

问题是：

* base64 会使请求体变大；
* 每次分析都要重复传输完整 PDF；
* 请求容易触发 timeout；
* 失败后无法复用已上传文件；
* 无法区分“文件上传失败”和“模型生成失败”；
* 不利于后续记录 PDF 与结构化结果之间的关系。

## Goal

将流程改为：

```text
PDF base64
  -> 后端 decode 为 PDF binary
  -> 上传到 OpenAI Files API
  -> 获取 file_id
  -> 使用 file_id 调用 Responses API
  -> 一次性生成结构化数据
  -> 保存 file_id、任务状态与结构化结果
```

核心目标：

* 避免将大体积 base64 PDF 直接塞进 LLM 请求；
* 支持复用 OpenAI `file_id`；
* 保持整本 PDF 的一次性全局分析能力；
* 输出严格结构化数据；
* 降低同步请求超时概率；
* 为后续教材知识图谱、章节结构抽取、概念体系生成打基础。

## Non-goals

本 issue 暂时不做：

* PDF chunking；
* RAG 检索；
* embedding；
* 向量数据库；
* 分页级别分析；
* section-level map-reduce；
* 多阶段 agent workflow。

这些可以作为后续优化，但当前优先实现一次性 file-based structured generation。

## Proposed Solution

### 1. 新增 PDF file upload 流程

后端接收前端传来的 base64 PDF 后，不再直接把 base64 放入 prompt。

应改为：

```text
base64 string
  -> decode bytes
  -> 写入临时 PDF 文件 / BytesIO
  -> OpenAI Files API upload
  -> 返回 file_id
```

上传时建议使用：

```text
purpose = "user_data"
```

OpenAI 文档说明，用作模型输入的文件建议使用 `user_data` purpose。([[OpenAI Developers](https://developers.openai.com/api/docs/guides/file-inputs?utm_source=chatgpt.com)][1])

### 2. 保存 file_id 与文件元信息

新增或扩展数据库字段，记录 OpenAI 文件信息。

建议字段：

```text
paper_id
openai_file_id
original_filename
file_size
file_hash
upload_status
uploaded_at
```

其中 `file_hash` 用于避免同一个 PDF 重复上传。

推荐逻辑：

```text
1. 计算 PDF hash
2. 查询本地是否已有相同 hash
3. 如果已有 openai_file_id，则复用
4. 如果没有，则上传到 OpenAI Files API
5. 保存 file_id
```

### 3. 使用 file_id 调用模型

上传成功后，通过 `file_id` 作为模型输入，而不是传 base64。

目标流程：

```text
Responses API input:
  - input_file: file_id
  - input_text: structured extraction instruction
```

OpenAI 的文件输入支持通过 `file_id` 引用已上传文件；PDF 输入会由支持视觉/文档能力的模型解析。([[OpenAI Developers](https://developers.openai.com/api/docs/guides/file-inputs?utm_source=chatgpt.com)][1])

示例伪代码：

```python
import base64
import io
from openai import OpenAI

client = OpenAI(timeout=900.0)

def upload_pdf_base64_to_openai(base64_pdf: str, filename: str) -> str:
    pdf_bytes = base64.b64decode(base64_pdf)

    file_obj = io.BytesIO(pdf_bytes)
    file_obj.name = filename

    uploaded = client.files.create(
        file=file_obj,
        purpose="user_data",
    )

    return uploaded.id


def generate_structured_data_from_file(file_id: str):
    response = client.responses.create(
        model="gpt-5.5",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": file_id,
                    },
                    {
                        "type": "input_text",
                        "text": """
请基于这份 PDF 一次性生成结构化数据。

要求：
1. 保留教材/论文的整体章节结构；
2. 抽取核心概念、定义、依赖关系、公式、案例；
3. 输出 JSON；
4. 不要只总结局部内容；
5. 如果某部分信息不足，请标记为 unknown，不要编造。
""",
                    },
                ],
            }
        ],
    )

    return response.output_text
```

### 4. 使用 Structured Outputs 约束 JSON

为了避免模型返回不稳定的自然语言，应使用 JSON Schema 约束输出。

OpenAI Structured Outputs 可以让模型输出遵循给定 JSON Schema，适合文档解析、信息抽取和结构化数据生成。([[OpenAI Developers](https://developers.openai.com/api/docs/guides/structured-outputs?utm_source=chatgpt.com)][2])

建议定义类似 schema：

```json
{
  "title": "string",
  "document_type": "textbook | paper | report | unknown",
  "chapters": [
    {
      "title": "string",
      "summary": "string",
      "concepts": [
        {
          "name": "string",
          "definition": "string",
          "prerequisites": ["string"],
          "related_concepts": ["string"],
          "evidence": "string"
        }
      ]
    }
  ],
  "global_concept_graph": {
    "nodes": [
      {
        "id": "string",
        "label": "string",
        "type": "concept | method | theorem | example | formula"
      }
    ],
    "edges": [
      {
        "source": "string",
        "target": "string",
        "relation": "prerequisite | related_to | part_of | applies_to | contrasts_with"
      }
    ]
  }
}
```

### 5. 对长任务使用 background mode

虽然使用 `file_id` 可以减少传输压力，但一次性分析整本教材仍然可能是长任务。

因此建议支持 background mode：

```text
POST /analyze
  -> 创建 OpenAI background response
  -> 保存 response_id
  -> 返回 job_id

GET /jobs/{job_id}
  -> 轮询 OpenAI response 状态
  -> 返回 pending / running / completed / failed
```

OpenAI background mode 适合长时间运行的 reasoning 任务，可以避免客户端连接超时或网络中断导致任务失败。([[OpenAI Developers](https://developers.openai.com/api/docs/guides/background?utm_source=chatgpt.com)][3])

### 6. 增加任务状态管理

建议新增分析任务状态：

```text
pending
uploading_file
file_uploaded
generating
completed
failed
```

需要保存：

```text
job_id
paper_id
openai_file_id
openai_response_id
status
error_message
result_json
created_at
updated_at
```

## Tasks

* [ ] 找到当前 base64 PDF 直接进入 LLM 请求的位置；
* [ ] 新增 `upload_pdf_base64_to_openai()` 方法；
* [ ] 后端将 base64 decode 为 binary 后上传 OpenAI Files API；
* [ ] 保存 `openai_file_id` 到数据库；
* [ ] 增加 PDF hash，避免重复上传；
* [ ] 新增基于 `file_id` 的 Responses API 调用；
* [ ] 设计结构化输出 JSON Schema；
* [ ] 将 prompt 改为“一次性全局结构化生成”；
* [ ] 增加超时配置；
* [ ] 支持 background mode / job polling；
* [ ] 保存 `response_id`、任务状态和最终结构化结果；
* [ ] 增加上传失败、生成失败、JSON schema 校验失败的错误处理；
* [ ] 写一个大 PDF 测试用例验证不再直接传 base64 到模型请求。

## Acceptance Criteria

完成后应满足：

1. LLM 分析请求中不再直接包含完整 base64 PDF；
2. PDF 会先上传到 OpenAI Files API，并获得 `file_id`；
3. 相同 PDF 可以复用已有 `file_id`；
4. 可以基于 `file_id` 一次性生成结构化数据；
5. 输出结果符合预定义 JSON Schema；
6. 长任务不会因为普通 HTTP 同步等待而直接失败；
7. 任务状态可以被查询；
8. 失败时能区分是文件上传失败、模型生成失败还是结构化校验失败；
9. 暂不引入 chunking、RAG、embedding 或向量数据库。

## Notes

这个 issue 的重点不是把 PDF 拆成 chunk，而是把：

```text
base64 PDF 直接塞进 LLM 请求
```

改成：

```text
base64 PDF -> OpenAI file upload -> file_id -> 一次性结构化生成
```

这样既保留模型对完整教材/论文的全局理解能力，又能减少请求体过大和同步超时带来的工程问题。