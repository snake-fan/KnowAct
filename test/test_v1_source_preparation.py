import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from backend.knowact.authoring.sources import (
    MinerUHTTPConfig,
    MinerUHTTPSourceParser,
    PublishedSourceURL,
    SourceParseError,
    resolve_or_create_parsed_markdown,
)


class V1SourcePreparationTest(unittest.TestCase):
    def test_resolve_or_create_parsed_markdown_passes_run_context_to_parser(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir) / "storage"
            pdf_path = storage_root / "books" / "isl_python.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4\nfixture\n%%EOF")
            parser = ContextCapturingSourceParser("## Parsed Markdown")

            material = resolve_or_create_parsed_markdown(
                pdf_path=pdf_path,
                storage_root=storage_root,
                parser=parser,
                force_reparse=True,
                run_id="dev_run_001",
                storage_uri="storage/books/isl_python.pdf",
            )

            self.assertEqual("generated", material.cache_status)
            self.assertEqual("storage/books/isl_python.md", material.storage_uri)
            self.assertEqual(
                [(pdf_path.resolve(), "dev_run_001", "storage/books/isl_python.pdf")],
                parser.calls,
            )

    def test_mineru_standard_mode_submits_signed_oss_url_to_extract_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "isl_python.pdf"
            _write_blank_pdf(pdf_path, pages=1)
            publisher = RecordingURLPublisher(
                PublishedSourceURL(
                    url="https://oss.example/isl_python.pdf?OSSAccessKeyId=key&Signature=secret",
                    object_key="knowact/mineru-staging/dev_run_001/books/isl_python-random.pdf",
                    expires_in_seconds=3600,
                )
            )
            parser = RecordingMinerUHTTPSourceParser(
                _standard_config(),
                source_url_publisher=publisher,
                zip_bytes=_markdown_zip("full.md", "## MinerU Markdown\n\nParsed."),
            )

            markdown = parser.parse_pdf_to_markdown(
                pdf_path=pdf_path,
                run_id="dev_run_001",
                storage_uri="storage/books/isl_python.pdf",
            )

            self.assertEqual("## MinerU Markdown\n\nParsed.", markdown)
            self.assertEqual(
                [(pdf_path, "dev_run_001", "storage/books/isl_python.pdf")],
                publisher.publish_calls,
            )
            self.assertEqual(
                ["knowact/mineru-staging/dev_run_001/books/isl_python-random.pdf"],
                publisher.cleanup_calls,
            )
            self.assertEqual(1, len(parser.posts))
            post_url, payload = parser.posts[0]
            self.assertEqual("https://mineru.test/api/v4/extract/task", post_url)
            self.assertEqual(
                "https://oss.example/isl_python.pdf?OSSAccessKeyId=key&Signature=secret",
                payload["url"],
            )
            self.assertEqual("vlm", payload["model_version"])
            self.assertEqual("ch", payload["language"])
            self.assertEqual("dev_run_001", payload["data_id"])
            self.assertNotIn("file-urls", post_url)
            self.assertEqual(["https://mineru.test/api/v4/extract/task/task_001"], parser.gets)
            self.assertEqual(["https://mineru.test/result-001.zip"], parser.downloads)

    def test_mineru_standard_mode_splits_large_pdf_and_joins_markdown_chunks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "large.pdf"
            _write_blank_pdf(pdf_path, pages=5)
            publisher = RecordingURLPublisher(
                PublishedSourceURL(
                    url="https://oss.example/chunk.pdf?OSSAccessKeyId=key&Signature=secret",
                    object_key="knowact/mineru-staging/dev_run_001/chunk.pdf",
                    expires_in_seconds=3600,
                )
            )
            parser = RecordingMinerUHTTPSourceParser(
                _standard_config(max_pages_per_task=2),
                source_url_publisher=publisher,
                zip_bytes=[
                    _markdown_zip("full.md", "# Chunk 1"),
                    _markdown_zip("full.md", "# Chunk 2"),
                    _markdown_zip("full.md", "# Chunk 3"),
                ],
            )

            markdown = parser.parse_pdf_to_markdown(
                pdf_path=pdf_path,
                run_id="dev_run_001",
                storage_uri="storage/books/large.pdf",
            )

            self.assertEqual(3, len(publisher.publish_calls))
            self.assertEqual(3, len(publisher.cleanup_calls))
            self.assertEqual(3, len(parser.posts))
            self.assertEqual(
                ["dev_run_001-chunk-001", "dev_run_001-chunk-002", "dev_run_001-chunk-003"],
                [payload["data_id"] for _, payload in parser.posts],
            )
            self.assertEqual(
                [
                    "large.pages-0001-0002.pdf",
                    "large.pages-0003-0004.pdf",
                    "large.pages-0005-0005.pdf",
                ],
                [call[0].name for call in publisher.publish_calls],
            )
            self.assertIn("source pages 1-2", markdown)
            self.assertIn("# Chunk 1", markdown)
            self.assertIn("source pages 3-4", markdown)
            self.assertIn("# Chunk 2", markdown)
            self.assertIn("source pages 5-5", markdown)
            self.assertIn("# Chunk 3", markdown)

    def test_mineru_standard_mode_rejects_signed_url_ttl_shorter_than_poll_window(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "isl_python.pdf"
            _write_blank_pdf(pdf_path, pages=1)
            publisher = RecordingURLPublisher(
                PublishedSourceURL(
                    url="https://oss.example/isl_python.pdf?Signature=secret",
                    object_key="knowact/mineru-staging/dev_run_001/isl_python-random.pdf",
                    expires_in_seconds=660,
                )
            )
            parser = RecordingMinerUHTTPSourceParser(
                _standard_config(max_wait_seconds=600),
                source_url_publisher=publisher,
                zip_bytes=_markdown_zip("full.md", "unused"),
            )

            with self.assertRaises(SourceParseError) as context:
                parser.parse_pdf_to_markdown(pdf_path=pdf_path, run_id="dev_run_001")

            self.assertIn("KNOWACT_OSS_SIGNED_URL_TTL_SECONDS", str(context.exception))
            self.assertEqual(
                ["knowact/mineru-staging/dev_run_001/isl_python-random.pdf"],
                publisher.cleanup_calls,
            )
            self.assertEqual([], parser.posts)


class ContextCapturingSourceParser:
    def __init__(self, markdown: str):
        self.markdown = markdown
        self.calls = []

    def parse_pdf_to_markdown(
        self,
        *,
        pdf_path: Path,
        run_id: str | None = None,
        storage_uri: str | None = None,
    ) -> str:
        self.calls.append((pdf_path, run_id, storage_uri))
        return self.markdown


class RecordingURLPublisher:
    def __init__(self, published_url: PublishedSourceURL):
        self.published_url = published_url
        self.publish_calls = []
        self.cleanup_calls = []

    def publish_pdf(
        self,
        *,
        pdf_path: Path,
        run_id: str | None = None,
        storage_uri: str | None = None,
    ) -> PublishedSourceURL:
        self.publish_calls.append((pdf_path, run_id, storage_uri))
        return self.published_url

    def cleanup_published_pdf(self, published_url: PublishedSourceURL) -> None:
        self.cleanup_calls.append(published_url.object_key)


class RecordingMinerUHTTPSourceParser(MinerUHTTPSourceParser):
    def __init__(
        self,
        config: MinerUHTTPConfig,
        *,
        source_url_publisher: RecordingURLPublisher,
        zip_bytes: bytes | list[bytes],
    ) -> None:
        super().__init__(config, source_url_publisher=source_url_publisher)
        self.zip_bytes = zip_bytes if isinstance(zip_bytes, list) else [zip_bytes]
        self.posts = []
        self.gets = []
        self.downloads = []

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        self.posts.append((url, payload))
        return {"code": 0, "data": {"task_id": f"task_{len(self.posts):03d}"}}

    def _get_json(self, url: str) -> dict[str, object]:
        self.gets.append(url)
        result_id = len(self.gets)
        return {
            "code": 0,
            "data": {
                "state": "done",
                "full_zip_url": f"https://mineru.test/result-{result_id:03d}.zip",
            },
        }

    def _download_bytes(self, url: str) -> bytes:
        self.downloads.append(url)
        return self.zip_bytes[len(self.downloads) - 1]


def _standard_config(
    *,
    max_wait_seconds: float = 600,
    max_pages_per_task: int = 200,
) -> MinerUHTTPConfig:
    return MinerUHTTPConfig(
        mode="standard",
        api_base_url="https://mineru.test/api/v4",
        api_token="token",
        model_version="vlm",
        language="ch",
        enable_table=True,
        is_ocr=False,
        enable_formula=True,
        timeout_seconds=1,
        max_wait_seconds=max_wait_seconds,
        poll_interval_seconds=0,
        max_pages_per_task=max_pages_per_task,
    )


def _write_blank_pdf(path: Path, *, pages: int) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


def _markdown_zip(name: str, text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
