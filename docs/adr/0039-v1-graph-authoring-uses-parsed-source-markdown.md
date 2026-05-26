# V1 graph authoring uses parsed source markdown for LLM input

KnowAct v1 graph authoring will parse local PDF source material into same-directory, same-stem Markdown before calling the LLM-backed graph authoring workflow. The workflow uses that Parsed Source Markdown as `SourceMaterial.text` instead of sending PDF base64 payloads or OpenAI file IDs, because the current remote LLM API path does not support file upload and direct PDF payloads have caused response timeouts.

**Considered Options**

- Send local PDFs to the model as base64 `input_file` payloads.
- Upload PDFs to OpenAI Files API and call the model with `file_id`.
- Parse PDFs with MinerU and send cached Markdown text to the LLM.

**Consequences**

The source-preparation step becomes part of authoring, and Markdown can be cached next to the original PDF for repeated runs. Visual image content is not used as model input in v1, but Markdown text, headings, formulas, tables, and figure captions remain available as source-grounding signals.
