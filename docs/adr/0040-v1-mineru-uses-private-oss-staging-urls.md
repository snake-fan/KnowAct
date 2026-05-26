# V1 MinerU source parsing uses private OSS staging URLs

KnowAct v1 will submit local PDF source material to MinerU standard mode by first uploading the PDF to a private Aliyun OSS staging object, generating a short-lived signed GET URL, and submitting that URL to MinerU v4. When a PDF exceeds MinerU's per-task page limit, KnowAct will split it locally into PDF chunks, submit each chunk through the same private OSS signed URL path, and concatenate the resulting Markdown in source page order. The OSS object is temporary source-preparation transport and is best-effort deleted after MinerU accepts or rejects the task.

**Considered Options**

- Make the OSS bucket or object public-read and give MinerU a stable public URL.
- Keep using MinerU-generated upload URLs and `PUT` the local PDF to MinerU.
- Upload to private OSS and give MinerU a short-lived signed URL.

**Consequences**

KnowAct can support MinerU's URL-based parsing path without exposing source PDFs as long-lived public files, and can handle large textbooks by splitting them before MinerU submission. The source-preparation path now depends on Aliyun OSS configuration, the `oss2` SDK, and PDF page splitting through `pypdf`, but ordinary unit tests use fake publishers and do not call real OSS or MinerU. Signed URLs must not be written into API responses, workflow logs, or candidate graph artifacts.
