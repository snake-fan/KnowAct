from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import io
import json
import logging
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import tempfile
import time
from typing import Literal, Protocol
from urllib import error, request
import uuid
import zipfile

from backend.knowact.logging_config import get_knowact_logger


MarkdownCacheStatus = Literal["hit", "generated", "regenerated"]
MinerUAPIMode = Literal["agent", "standard"]
_LOGGER = get_knowact_logger("authoring.sources")
_SAFE_OBJECT_PART_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")
_SIGNED_QUERY_PATTERN = re.compile(
    r"([?&](?:OSSAccessKeyId|Expires|Signature|security-token|x-oss-[^=]+)=)[^&\s]+",
    re.IGNORECASE,
)


class SourceParser(Protocol):
    def parse_pdf_to_markdown(
        self,
        *,
        pdf_path: Path,
        run_id: str | None = None,
        storage_uri: str | None = None,
    ) -> str:
        """Parse one local PDF file into Markdown text."""


class SourceURLPublisher(Protocol):
    def publish_pdf(
        self,
        *,
        pdf_path: Path,
        run_id: str | None = None,
        storage_uri: str | None = None,
    ) -> "PublishedSourceURL":
        """Publish a local PDF at a short-lived URL that an external parser can fetch."""

    def cleanup_published_pdf(self, published_url: "PublishedSourceURL") -> None:
        """Best-effort cleanup for a previously published PDF URL."""


class SourcePreparationError(ValueError):
    """Raised when source material cannot be prepared for graph authoring."""


class SourceParseError(SourcePreparationError):
    """Raised when a source parser cannot produce Markdown."""


class SourcePublishError(SourcePreparationError):
    """Raised when a local source material cannot be published for parsing."""


class ParsedMarkdownEmptyError(SourcePreparationError):
    """Raised when Parsed Source Markdown is empty."""


class ParsedMarkdownWriteError(SourcePreparationError):
    """Raised when Parsed Source Markdown cannot be written."""


@dataclass(frozen=True)
class ParsedMarkdownMaterial:
    path: Path
    storage_uri: str
    filename: str
    size_bytes: int
    cache_status: MarkdownCacheStatus
    text: str


@dataclass(frozen=True)
class PublishedSourceURL:
    url: str
    object_key: str | None = None
    expires_in_seconds: int | None = None


@dataclass(frozen=True)
class PDFPageChunk:
    path: Path
    index: int
    total_chunks: int
    first_page: int
    last_page: int

    @property
    def label(self) -> str:
        return f"{self.index}/{self.total_chunks} pages {self.first_page}-{self.last_page}"


@dataclass(frozen=True)
class AliyunOSSConfig:
    endpoint: str
    bucket_name: str
    access_key_id: str
    access_key_secret: str
    object_prefix: str = "knowact/mineru-staging"
    signed_url_ttl_seconds: int = 3600
    keep_staging_objects: bool = False

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "AliyunOSSConfig":
        env = os.environ if environ is None else environ
        config = cls(
            endpoint=_required_env(env, "ALIYUN_OSS_ENDPOINT"),
            bucket_name=_required_env(env, "ALIYUN_OSS_BUCKET"),
            access_key_id=_required_env(env, "ALIYUN_OSS_ACCESS_KEY_ID"),
            access_key_secret=_required_env(env, "ALIYUN_OSS_ACCESS_KEY_SECRET"),
            object_prefix=_env(env, "KNOWACT_OSS_OBJECT_PREFIX") or "knowact/mineru-staging",
            signed_url_ttl_seconds=_int_env(
                env,
                "KNOWACT_OSS_SIGNED_URL_TTL_SECONDS",
                default=3600,
            ),
            keep_staging_objects=_bool_env(env, "KNOWACT_OSS_KEEP_STAGING_OBJECTS", default=False),
        )
        if config.signed_url_ttl_seconds <= 0:
            raise ValueError("KNOWACT_OSS_SIGNED_URL_TTL_SECONDS must be positive")
        if not config.object_prefix.strip().strip("/"):
            raise ValueError("KNOWACT_OSS_OBJECT_PREFIX must not be blank")
        if ".oss-" in config.bucket_name or config.bucket_name.endswith(".aliyuncs.com"):
            raise ValueError("ALIYUN_OSS_BUCKET must be the bucket name, not a bucket domain")
        return config


@dataclass(frozen=True)
class MinerUHTTPConfig:
    mode: MinerUAPIMode = "agent"
    api_base_url: str = "https://mineru.net/api/v1/agent"
    api_token: str | None = None
    model_version: str = "vlm"
    language: str = "ch"
    enable_table: bool = True
    is_ocr: bool = False
    enable_formula: bool = True
    page_range: str | None = None
    timeout_seconds: float = 30.0
    max_wait_seconds: float = 600.0
    poll_interval_seconds: float = 3.0
    max_pages_per_task: int = 200

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "MinerUHTTPConfig":
        env = os.environ if environ is None else environ
        mode = _env(env, "KNOWACT_MINERU_API_MODE") or "agent"
        if mode not in {"agent", "standard"}:
            raise ValueError("KNOWACT_MINERU_API_MODE must be agent or standard")

        default_base_url = (
            "https://mineru.net/api/v1/agent"
            if mode == "agent"
            else "https://mineru.net/api/v4"
        )
        config = cls(
            mode=mode,
            api_base_url=(_env(env, "KNOWACT_MINERU_API_BASE_URL") or default_base_url).rstrip("/"),
            api_token=_env(env, "KNOWACT_MINERU_API_TOKEN"),
            model_version=_env(env, "KNOWACT_MINERU_MODEL_VERSION") or "vlm",
            language=_env(env, "KNOWACT_MINERU_LANGUAGE") or "ch",
            enable_table=_bool_env(env, "KNOWACT_MINERU_ENABLE_TABLE", default=True),
            is_ocr=_bool_env(env, "KNOWACT_MINERU_IS_OCR", default=False),
            enable_formula=_bool_env(env, "KNOWACT_MINERU_ENABLE_FORMULA", default=True),
            page_range=_env(env, "KNOWACT_MINERU_PAGE_RANGE"),
            timeout_seconds=_float_env(env, "KNOWACT_MINERU_TIMEOUT_SECONDS", default=30.0),
            max_wait_seconds=_float_env(env, "KNOWACT_MINERU_MAX_WAIT_SECONDS", default=600.0),
            poll_interval_seconds=_float_env(env, "KNOWACT_MINERU_POLL_INTERVAL_SECONDS", default=3.0),
            max_pages_per_task=_int_env(env, "KNOWACT_MINERU_MAX_PAGES_PER_TASK", default=200),
        )
        if config.max_pages_per_task <= 0:
            raise ValueError("KNOWACT_MINERU_MAX_PAGES_PER_TASK must be positive")
        return config


class AliyunOSSSourceURLPublisher:
    """Publishes local PDFs through private Aliyun OSS objects and signed GET URLs."""

    def __init__(self, config: AliyunOSSConfig | None = None) -> None:
        try:
            self._config = config or AliyunOSSConfig.from_env()
        except ValueError as exc:
            raise SourcePublishError(f"Aliyun OSS source URL publisher is not configured: {exc}") from exc
        self._bucket = None

    def publish_pdf(
        self,
        *,
        pdf_path: Path,
        run_id: str | None = None,
        storage_uri: str | None = None,
    ) -> PublishedSourceURL:
        object_key = _build_oss_staging_object_key(
            object_prefix=self._config.object_prefix,
            pdf_path=pdf_path,
            run_id=run_id,
            storage_uri=storage_uri,
        )
        bucket = self._get_bucket()
        uploaded = False
        _LOGGER.info(
            "Aliyun OSS staging upload started object_key=%s filename=%s size_bytes=%d run_id=%s",
            object_key,
            pdf_path.name,
            pdf_path.stat().st_size,
            run_id,
        )
        try:
            bucket.put_object_from_file(object_key, str(pdf_path))
            uploaded = True
            _LOGGER.info(
                "Aliyun OSS staging upload succeeded object_key=%s run_id=%s",
                object_key,
                run_id,
            )
            signed_url = bucket.sign_url("GET", object_key, self._config.signed_url_ttl_seconds)
            _LOGGER.info(
                "Aliyun OSS signed URL created object_key=%s ttl_seconds=%d run_id=%s",
                object_key,
                self._config.signed_url_ttl_seconds,
                run_id,
            )
        except Exception as exc:
            _LOGGER.error(
                "Aliyun OSS staging publish failed object_key=%s run_id=%s error_type=%s",
                object_key,
                run_id,
                type(exc).__name__,
            )
            if uploaded:
                self._best_effort_delete(object_key)
            raise SourcePublishError(
                f"Aliyun OSS source URL publish failed for object {object_key}: {type(exc).__name__}"
            ) from exc

        return PublishedSourceURL(
            url=signed_url,
            object_key=object_key,
            expires_in_seconds=self._config.signed_url_ttl_seconds,
        )

    def cleanup_published_pdf(self, published_url: PublishedSourceURL) -> None:
        object_key = published_url.object_key
        if object_key is None:
            _LOGGER.info("Aliyun OSS staging cleanup skipped because object key is unavailable")
            return
        if self._config.keep_staging_objects:
            _LOGGER.info(
                "Aliyun OSS staging cleanup skipped by config object_key=%s",
                object_key,
            )
            return
        self._best_effort_delete(object_key)

    def _best_effort_delete(self, object_key: str) -> None:
        try:
            self._get_bucket().delete_object(object_key)
            _LOGGER.info("Aliyun OSS staging object deleted object_key=%s", object_key)
        except Exception as exc:
            _LOGGER.warning(
                "Aliyun OSS staging object cleanup failed object_key=%s error_type=%s",
                object_key,
                type(exc).__name__,
            )

    def _get_bucket(self):
        if self._bucket is not None:
            return self._bucket
        try:
            import oss2
        except ImportError as exc:
            raise SourcePublishError(
                "oss2 package is required for Aliyun OSS source URL publishing"
            ) from exc
        auth = oss2.Auth(self._config.access_key_id, self._config.access_key_secret)
        self._bucket = oss2.Bucket(auth, self._config.endpoint, self._config.bucket_name)
        return self._bucket


class MinerUHTTPSourceParser:
    """MinerU-backed parser that turns a local PDF into Markdown text."""

    def __init__(
        self,
        config: MinerUHTTPConfig | None = None,
        *,
        source_url_publisher: SourceURLPublisher | None = None,
    ) -> None:
        self._config = config or MinerUHTTPConfig.from_env()
        self._source_url_publisher = source_url_publisher

    def parse_pdf_to_markdown(
        self,
        *,
        pdf_path: Path,
        run_id: str | None = None,
        storage_uri: str | None = None,
    ) -> str:
        if self._config.mode == "standard":
            return self._parse_with_standard_api(pdf_path, run_id=run_id, storage_uri=storage_uri)
        return self._parse_with_agent_api(pdf_path)

    def _parse_with_agent_api(self, pdf_path: Path) -> str:
        payload = _agent_parse_payload(pdf_path.name, self._config)
        _LOGGER.info(
            "MinerU agent parse request started filename=%s mode=%s",
            pdf_path.name,
            self._config.mode,
        )
        created = self._post_json(f"{self._config.api_base_url}/parse/file", payload)
        data = _response_data(created, "MinerU parse/file")
        task_id = _required_str(data, "task_id", "MinerU parse/file")
        file_url = _required_str(data, "file_url", "MinerU parse/file")
        _LOGGER.info("MinerU agent parse task created task_id=%s filename=%s", task_id, pdf_path.name)

        _LOGGER.info("MinerU agent upload started task_id=%s filename=%s", task_id, pdf_path.name)
        self._put_file(file_url, pdf_path)
        _LOGGER.info("MinerU agent upload succeeded task_id=%s filename=%s", task_id, pdf_path.name)
        result = self._poll_agent_result(task_id)
        markdown_url = _required_str(result, "markdown_url", "MinerU parse result")
        _LOGGER.info("MinerU agent markdown download started task_id=%s", task_id)
        return self._download_text(markdown_url)

    def _parse_with_standard_api(
        self,
        pdf_path: Path,
        *,
        run_id: str | None,
        storage_uri: str | None,
    ) -> str:
        if not self._config.api_token:
            raise SourceParseError("KNOWACT_MINERU_API_TOKEN is required for standard MinerU API mode")

        page_count = _pdf_page_count(pdf_path)
        if page_count <= self._config.max_pages_per_task:
            return self._parse_standard_pdf_task(
                pdf_path,
                run_id=run_id,
                storage_uri=storage_uri,
                data_id=run_id or pdf_path.stem,
                chunk=None,
            )

        if self._config.page_range:
            raise SourceParseError(
                "KNOWACT_MINERU_PAGE_RANGE is not supported when a PDF must be split for "
                "KNOWACT_MINERU_MAX_PAGES_PER_TASK"
            )

        _LOGGER.info(
            "PDF exceeds MinerU page limit; splitting filename=%s page_count=%d max_pages_per_task=%d run_id=%s",
            pdf_path.name,
            page_count,
            self._config.max_pages_per_task,
            run_id,
        )
        markdown_chunks: list[str] = []
        with tempfile.TemporaryDirectory(prefix="knowact-mineru-pdf-chunks-") as temp_dir:
            chunks = _split_pdf_into_page_chunks(
                pdf_path=pdf_path,
                max_pages_per_chunk=self._config.max_pages_per_task,
                output_dir=Path(temp_dir),
            )
            for chunk in chunks:
                _LOGGER.info(
                    "MinerU standard chunk parse started chunk=%s filename=%s run_id=%s",
                    chunk.label,
                    chunk.path.name,
                    run_id,
                )
                markdown_chunks.append(
                    self._parse_standard_pdf_task(
                        chunk.path,
                        run_id=run_id,
                        storage_uri=storage_uri,
                        data_id=f"{run_id or pdf_path.stem}-chunk-{chunk.index:03d}",
                        chunk=chunk,
                    )
                )
        return _join_markdown_chunks(markdown_chunks, chunks)

    def _parse_standard_pdf_task(
        self,
        pdf_path: Path,
        *,
        run_id: str | None,
        storage_uri: str | None,
        data_id: str,
        chunk: PDFPageChunk | None,
    ) -> str:
        publisher = self._source_url_publisher or AliyunOSSSourceURLPublisher()
        published_url = publisher.publish_pdf(
            pdf_path=pdf_path,
            run_id=run_id,
            storage_uri=storage_uri,
        )
        try:
            _validate_published_url_ttl(published_url, self._config)
            _LOGGER.info(
                "MinerU standard URL parse request preparing filename=%s object_key=%s ttl_seconds=%s run_id=%s",
                pdf_path.name,
                published_url.object_key,
                published_url.expires_in_seconds,
                run_id,
            )
            payload = _standard_url_extract_payload(
                signed_url=published_url.url,
                pdf_path=pdf_path,
                run_id=run_id,
                data_id=data_id,
                config=self._config,
            )
            created = self._post_json(f"{self._config.api_base_url}/extract/task", payload)
            data = _response_data(created, "MinerU extract/task")
            task_id = _required_str(data, "task_id", "MinerU extract/task")
            _LOGGER.info(
                "MinerU standard URL parse task created task_id=%s filename=%s object_key=%s run_id=%s chunk=%s",
                task_id,
                pdf_path.name,
                published_url.object_key,
                run_id,
                chunk.label if chunk is not None else "none",
            )
            result = self._poll_standard_result(task_id, chunk=chunk)
        finally:
            publisher.cleanup_published_pdf(published_url)

        zip_url = _required_str(result, "full_zip_url", "MinerU standard result")
        _LOGGER.info(
            "MinerU standard result zip download started task_id=%s chunk=%s",
            task_id,
            chunk.label if chunk is not None else "none",
        )
        zip_bytes = self._download_bytes(zip_url)
        _LOGGER.info(
            "MinerU standard result zip downloaded task_id=%s size_bytes=%d chunk=%s",
            task_id,
            len(zip_bytes),
            chunk.label if chunk is not None else "none",
        )
        markdown = _extract_markdown_from_zip(zip_bytes)
        _LOGGER.info(
            "MinerU standard Markdown extracted task_id=%s size_chars=%d chunk=%s",
            task_id,
            len(markdown),
            chunk.label if chunk is not None else "none",
        )
        return markdown

    def _poll_agent_result(self, task_id: str) -> dict[str, object]:
        deadline = time.monotonic() + self._config.max_wait_seconds
        while time.monotonic() < deadline:
            payload = self._get_json(f"{self._config.api_base_url}/parse/{task_id}")
            data = _response_data(payload, "MinerU parse result")
            state = data.get("state")
            _LOGGER.info("MinerU agent parse poll task_id=%s state=%s", task_id, state)
            if state == "done":
                _LOGGER.info("MinerU agent parse completed task_id=%s", task_id)
                return data
            if state == "failed":
                _LOGGER.error("MinerU agent parse failed task_id=%s", task_id)
                raise SourceParseError(str(data.get("err_msg") or "MinerU parse failed"))
            time.sleep(self._config.poll_interval_seconds)
        raise SourceParseError(f"MinerU parse timed out after {self._config.max_wait_seconds} seconds")

    def _poll_standard_result(self, task_id: str, *, chunk: PDFPageChunk | None = None) -> dict[str, object]:
        deadline = time.monotonic() + self._config.max_wait_seconds
        while time.monotonic() < deadline:
            payload = self._get_json(f"{self._config.api_base_url}/extract/task/{task_id}")
            data = _response_data(payload, "MinerU extract/task result")
            state = data.get("state")
            _LOGGER.info(
                "MinerU standard URL parse poll task_id=%s state=%s chunk=%s",
                task_id,
                state,
                chunk.label if chunk is not None else "none",
            )
            if state == "done":
                _LOGGER.info(
                    "MinerU standard URL parse completed task_id=%s chunk=%s",
                    task_id,
                    chunk.label if chunk is not None else "none",
                )
                return data
            if state == "failed":
                message = _redact_signed_url(str(data.get("err_msg") or "MinerU parse failed"))
                _LOGGER.error(
                    "MinerU standard URL parse failed task_id=%s chunk=%s message=%s",
                    task_id,
                    chunk.label if chunk is not None else "none",
                    message,
                )
                raise SourceParseError(message)
            time.sleep(self._config.poll_interval_seconds)
        raise SourceParseError(f"MinerU parse timed out after {self._config.max_wait_seconds} seconds")

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if self._config.api_token:
            headers["Authorization"] = f"Bearer {self._config.api_token}"
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        return self._open_json(req)

    def _get_json(self, url: str) -> dict[str, object]:
        headers = {"Accept": "*/*"}
        if self._config.api_token:
            headers["Authorization"] = f"Bearer {self._config.api_token}"
        return self._open_json(request.Request(url, headers=headers, method="GET"))

    def _put_file(self, url: str, pdf_path: Path) -> None:
        req = request.Request(url, data=pdf_path.read_bytes(), method="PUT")
        try:
            with request.urlopen(req, timeout=self._config.timeout_seconds) as response:
                if response.status >= 400:
                    raise SourceParseError(f"MinerU file upload failed with HTTP {response.status}")
        except error.URLError as exc:
            raise SourceParseError(f"MinerU file upload failed: {exc}") from exc

    def _download_text(self, url: str) -> str:
        return self._download_bytes(url).decode("utf-8")

    def _download_bytes(self, url: str) -> bytes:
        try:
            with request.urlopen(url, timeout=self._config.timeout_seconds) as response:
                return response.read()
        except error.URLError as exc:
            raise SourceParseError(f"MinerU result download failed: {exc}") from exc

    def _open_json(self, req: request.Request) -> dict[str, object]:
        try:
            with request.urlopen(req, timeout=self._config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            raise SourceParseError(f"MinerU request failed: {exc}") from exc
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SourceParseError("MinerU response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise SourceParseError("MinerU response was not a JSON object")
        code = payload.get("code")
        if code not in (0, None):
            raise SourceParseError(_redact_signed_url(str(payload.get("msg") or f"MinerU returned code {code}")))
        return payload


def resolve_or_create_parsed_markdown(
    *,
    pdf_path: Path,
    storage_root: Path,
    parser: SourceParser,
    force_reparse: bool = False,
    run_id: str | None = None,
    storage_uri: str | None = None,
) -> ParsedMarkdownMaterial:
    root = storage_root.resolve()
    resolved_pdf_path = pdf_path.resolve()
    markdown_path = resolved_pdf_path.with_suffix(".md")
    try:
        markdown_path.relative_to(root)
    except ValueError as exc:
        raise SourcePreparationError("Parsed Source Markdown path must stay under storage/") from exc

    if markdown_path.exists() and not force_reparse:
        return _read_markdown_material(markdown_path, root, cache_status="hit")

    cache_status: MarkdownCacheStatus = "regenerated" if markdown_path.exists() else "generated"
    try:
        markdown_text = parser.parse_pdf_to_markdown(
            pdf_path=resolved_pdf_path,
            run_id=run_id,
            storage_uri=storage_uri,
        )
    except SourcePreparationError:
        raise
    except Exception as exc:
        raise SourceParseError(f"MinerU source parsing failed: {exc}") from exc

    markdown_text = _validate_markdown_text(markdown_text)
    try:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown_text, encoding="utf-8")
    except OSError as exc:
        raise ParsedMarkdownWriteError(f"Could not write Parsed Source Markdown: {exc}") from exc

    return _read_markdown_material(markdown_path, root, cache_status=cache_status)


def _read_markdown_material(
    markdown_path: Path,
    storage_root: Path,
    *,
    cache_status: MarkdownCacheStatus,
) -> ParsedMarkdownMaterial:
    try:
        text = markdown_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SourcePreparationError(f"Could not read Parsed Source Markdown: {exc}") from exc
    text = _validate_markdown_text(text)
    size_bytes = markdown_path.stat().st_size
    return ParsedMarkdownMaterial(
        path=markdown_path,
        storage_uri=f"storage/{markdown_path.resolve().relative_to(storage_root).as_posix()}",
        filename=markdown_path.name,
        size_bytes=size_bytes,
        cache_status=cache_status,
        text=text,
    )


def _validate_markdown_text(text: str) -> str:
    if not text.strip():
        raise ParsedMarkdownEmptyError("Parsed Source Markdown is empty")
    return text


def _agent_parse_payload(file_name: str, config: MinerUHTTPConfig) -> dict[str, object]:
    payload: dict[str, object] = {
        "file_name": file_name,
        "language": config.language,
        "enable_table": config.enable_table,
        "is_ocr": config.is_ocr,
        "enable_formula": config.enable_formula,
    }
    if config.page_range:
        payload["page_range"] = config.page_range
    return payload


def _standard_url_extract_payload(
    *,
    signed_url: str,
    pdf_path: Path,
    run_id: str | None,
    data_id: str,
    config: MinerUHTTPConfig,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "url": signed_url,
        "model_version": config.model_version,
        "language": config.language,
        "enable_table": config.enable_table,
        "is_ocr": config.is_ocr,
        "enable_formula": config.enable_formula,
        "data_id": _safe_data_id(data_id or run_id or pdf_path.stem),
    }
    if config.page_range:
        payload["page_ranges"] = config.page_range
    return payload


def _validate_published_url_ttl(
    published_url: PublishedSourceURL,
    config: MinerUHTTPConfig,
) -> None:
    expires_in_seconds = published_url.expires_in_seconds
    if expires_in_seconds is None:
        return
    required_seconds = config.max_wait_seconds + 60
    if expires_in_seconds <= required_seconds:
        raise SourceParseError(
            "KNOWACT_OSS_SIGNED_URL_TTL_SECONDS must be greater than "
            f"KNOWACT_MINERU_MAX_WAIT_SECONDS + 60 seconds; got {expires_in_seconds}, "
            f"need more than {required_seconds}"
        )


def _response_data(payload: dict[str, object], context: str) -> dict[str, object]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SourceParseError(f"{context} response did not include a data object")
    return data


def _required_str(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SourceParseError(f"{context} response did not include {key}")
    return value


def _build_oss_staging_object_key(
    *,
    object_prefix: str,
    pdf_path: Path,
    run_id: str | None,
    storage_uri: str | None,
) -> str:
    prefix = object_prefix.strip("/")
    run_part = _safe_object_part(run_id or "manual")
    source_parts = _source_storage_parts(pdf_path=pdf_path, storage_uri=storage_uri)
    filename = source_parts[-1]
    stem = pdf_path.stem or Path(filename).stem or "source"
    suffix = pdf_path.suffix.lower() or Path(filename).suffix.lower() or ".pdf"
    object_name = f"{_safe_object_part(stem)}-{uuid.uuid4().hex}{suffix}"
    directory_parts = [_safe_object_part(part) for part in source_parts[:-1]]
    return "/".join(part for part in (prefix, run_part, *directory_parts, object_name) if part)


def _source_storage_parts(*, pdf_path: Path, storage_uri: str | None) -> list[str]:
    if storage_uri is not None and storage_uri.strip():
        uri = storage_uri.strip()
        relative_uri = uri.removeprefix("storage/") if uri.startswith("storage/") else uri
        parts = [part for part in PurePosixPath(relative_uri).parts if part not in {"", ".", ".."}]
        if parts:
            return list(parts)
    return [pdf_path.name]


def _safe_object_part(value: str) -> str:
    cleaned = _SAFE_OBJECT_PART_PATTERN.sub("_", value.strip()).strip("._-")
    return cleaned or "item"


def _safe_data_id(value: str) -> str:
    cleaned = _SAFE_OBJECT_PART_PATTERN.sub("_", value.strip()).strip("._-")
    return (cleaned or "source")[:128]


def _pdf_page_count(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader

        with _quiet_pypdf_warnings():
            reader = PdfReader(pdf_path)
            return len(reader.pages)
    except Exception as exc:
        raise SourceParseError(f"Could not inspect PDF page count: {type(exc).__name__}") from exc


def _split_pdf_into_page_chunks(
    *,
    pdf_path: Path,
    max_pages_per_chunk: int,
    output_dir: Path,
) -> tuple[PDFPageChunk, ...]:
    try:
        from pypdf import PdfReader, PdfWriter

        with _quiet_pypdf_warnings():
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)
            chunks: list[PDFPageChunk] = []
            total_chunks = (page_count + max_pages_per_chunk - 1) // max_pages_per_chunk
            for chunk_index, start_index in enumerate(range(0, page_count, max_pages_per_chunk), start=1):
                end_index = min(start_index + max_pages_per_chunk, page_count)
                writer = PdfWriter()
                for page_index in range(start_index, end_index):
                    writer.add_page(reader.pages[page_index])

                first_page = start_index + 1
                last_page = end_index
                chunk_path = output_dir / (
                    f"{pdf_path.stem}.pages-{first_page:04d}-{last_page:04d}.pdf"
                )
                with chunk_path.open("wb") as handle:
                    writer.write(handle)
                chunks.append(
                    PDFPageChunk(
                        path=chunk_path,
                        index=chunk_index,
                        total_chunks=total_chunks,
                        first_page=first_page,
                        last_page=last_page,
                    )
                )
            return tuple(chunks)
    except SourceParseError:
        raise
    except Exception as exc:
        raise SourceParseError(f"Could not split PDF for MinerU page limit: {type(exc).__name__}") from exc


def _join_markdown_chunks(markdown_chunks: list[str], chunks: tuple[PDFPageChunk, ...]) -> str:
    if len(markdown_chunks) != len(chunks):
        raise SourceParseError("MinerU Markdown chunk count did not match PDF chunk count")
    sections = []
    for markdown, chunk in zip(markdown_chunks, chunks, strict=True):
        sections.append(
            "\n\n".join(
                (
                    f"<!-- MinerU parsed PDF chunk {chunk.index}/{chunk.total_chunks}: "
                    f"source pages {chunk.first_page}-{chunk.last_page} -->",
                    markdown.strip(),
                )
            )
        )
    return "\n\n".join(sections)


@contextmanager
def _quiet_pypdf_warnings():
    logger_names = ("pypdf", "pypdf._reader")
    previous_levels = {name: logging.getLogger(name).level for name in logger_names}
    try:
        for name in logger_names:
            logging.getLogger(name).setLevel(logging.ERROR)
        yield
    finally:
        for name, level in previous_levels.items():
            logging.getLogger(name).setLevel(level)


def _extract_markdown_from_zip(zip_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            names = archive.namelist()
            preferred = [name for name in names if name.endswith("full.md")]
            candidates = preferred or [name for name in names if name.endswith(".md")]
            if not candidates:
                raise SourceParseError("MinerU result zip did not include Markdown")
            with archive.open(candidates[0]) as handle:
                return handle.read().decode("utf-8")
    except zipfile.BadZipFile as exc:
        raise SourceParseError("MinerU result was not a valid zip file") from exc


def _required_env(environ: Mapping[str, str], key: str) -> str:
    value = _env(environ, key)
    if value is None:
        raise ValueError(f"{key} is required")
    return value


def _env(environ: Mapping[str, str], key: str) -> str | None:
    value = environ.get(key)
    if value is None or not value.strip():
        return None
    return value


def _float_env(environ: Mapping[str, str], key: str, *, default: float) -> float:
    value = _env(environ, key)
    if value is None:
        return default
    return float(value)


def _int_env(environ: Mapping[str, str], key: str, *, default: int) -> int:
    value = _env(environ, key)
    if value is None:
        return default
    return int(value)


def _bool_env(environ: Mapping[str, str], key: str, *, default: bool) -> bool:
    value = _env(environ, key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _redact_signed_url(value: str) -> str:
    return _SIGNED_QUERY_PATTERN.sub(r"\1[REDACTED]", value)
