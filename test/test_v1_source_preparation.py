from io import BytesIO
import tempfile
import unittest
from pathlib import Path

from backend.knowact.storage.source_material_catalog import (
    MaterialFileError,
    MaterialFileIntegrityError,
    MaterialFileTypeError,
    list_source_materials,
    load_markdown_source_material,
    save_markdown_source_material,
)


class V1MarkdownSourceCatalogTest(unittest.TestCase):
    def test_catalog_round_trips_utf8_markdown_with_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            text = "# 主题\n\n训练误差与测试误差。"

            record = save_markdown_source_material(
                storage_root=storage_root,
                source_id="isl_scope",
                title="Scoped ISL",
                filename="isl.md",
                content=BytesIO(text.encode("utf-8")),
                citation="fixture citation",
            )
            loaded = load_markdown_source_material(
                storage_root=storage_root,
                source_id="isl_scope",
            )

            self.assertEqual(text, loaded.text)
            self.assertEqual(record, loaded.record)
            self.assertEqual(64, len(record.content_sha256 or ""))
            self.assertEqual((record,), list_source_materials(storage_root=storage_root))

    def test_catalog_rejects_non_markdown_and_non_utf8_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            with self.assertRaises(MaterialFileTypeError):
                save_markdown_source_material(
                    storage_root=storage_root,
                    source_id="pdf",
                    title="PDF",
                    filename="book.pdf",
                    content=BytesIO(b"%PDF"),
                )
            with self.assertRaises(MaterialFileError):
                save_markdown_source_material(
                    storage_root=storage_root,
                    source_id="binary",
                    title="Binary",
                    filename="book.md",
                    content=BytesIO(b"\xff\xfe"),
                )

    def test_catalog_detects_content_changes_after_upload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            record = save_markdown_source_material(
                storage_root=storage_root,
                source_id="source",
                title="Source",
                filename="source.md",
                content=BytesIO(b"# Source\n\nOriginal content."),
            )
            path = storage_root / record.storage_path
            path.write_text("# Source\n\nModified content.", encoding="utf-8")

            with self.assertRaises(MaterialFileIntegrityError):
                load_markdown_source_material(storage_root=storage_root, source_id="source")

    def test_catalog_ignores_legacy_pdf_metadata_when_listing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            legacy_dir = storage_root / "source_materials" / "legacy"
            legacy_dir.mkdir(parents=True)
            (legacy_dir / "metadata.json").write_text(
                """{
  "source_id": "legacy",
  "title": "Legacy PDF",
  "storage_path": "source_materials/legacy/original.pdf",
  "storage_uri": "storage/source_materials/legacy/original.pdf",
  "filename": "legacy.pdf",
  "size_bytes": 4,
  "uploaded_at": "2026-01-01T00:00:00Z"
}
""",
                encoding="utf-8",
            )

            self.assertEqual((), list_source_materials(storage_root=storage_root))


if __name__ == "__main__":
    unittest.main()
