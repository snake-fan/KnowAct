import re
from dataclasses import dataclass
from collections.abc import Sequence

from backend.knowact.authoring.schemas import ParsedSourceSegment, SourceMaterial
from backend.knowact.core.graph import SourceLocator


MAX_SEGMENT_CHARS = 12000
MIN_SEGMENT_CHARS = 800
OVERLAP_PARAGRAPHS = 1

_MARKDOWN_HEADING_PATTERN = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
_NUMBERED_HEADING_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+){0,2})(?:[\s:.-]+)(.+?)\s*$")
_HTML_COMMENT_PATTERN = re.compile(r"^\s*<!--.*-->\s*$")
_TOC_HEADING_PATTERN = re.compile(r"^(contents|table of contents)\b", re.IGNORECASE)


@dataclass(frozen=True)
class _RawSection:
    source: SourceMaterial
    heading_path: tuple[str, ...]
    text: str

    @property
    def parent_path(self) -> tuple[str, ...]:
        return self.heading_path[:-1]

    @property
    def char_count(self) -> int:
        return len(self.text)


def derive_parsed_source_segments(
    source_materials: Sequence[SourceMaterial],
) -> tuple[ParsedSourceSegment, ...]:
    raw_sections: list[_RawSection] = []
    for source in source_materials:
        raw_sections.extend(_merge_small_sibling_sections(_parse_source_sections(source)))

    segments: list[ParsedSourceSegment] = []
    next_index = 1
    for section in raw_sections:
        for text, suffix in _split_oversized_text(section.text):
            location = _render_location(section.heading_path, suffix)
            segments.append(
                ParsedSourceSegment(
                    segment_id=f"seg_{next_index:06d}",
                    source_id=section.source.source_id,
                    source_title=section.source.title,
                    location=location,
                    heading_path=section.heading_path,
                    source_locator=SourceLocator(
                        source_id=section.source.source_id,
                        locator=location,
                        note="Parsed source segment",
                    ),
                    text=text,
                    char_count=len(text),
                )
            )
            next_index += 1
    return tuple(segments)


def _parse_source_sections(source: SourceMaterial) -> tuple[_RawSection, ...]:
    heading_stack: list[str] = []
    current_heading_path: tuple[str, ...] | None = None
    current_lines: list[str] = []
    sections: list[_RawSection] = []
    skipping_toc = False

    for raw_line in source.text.splitlines():
        line = raw_line.rstrip()
        if _is_structural_noise(line):
            continue

        heading = _parse_heading(line)
        if heading is not None:
            level, title = heading
            if _TOC_HEADING_PATTERN.match(title):
                skipping_toc = True
                _flush_section(source, current_heading_path, current_lines, sections)
                current_heading_path = None
                current_lines = []
                continue

            if skipping_toc and _looks_like_toc_line(title):
                continue
            skipping_toc = False

            _flush_section(source, current_heading_path, current_lines, sections)
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(title)
            current_heading_path = tuple(heading_stack[:3])
            current_lines = []
            continue

        if skipping_toc and _looks_like_toc_line(line):
            continue
        skipping_toc = False
        current_lines.append(line)

    _flush_section(source, current_heading_path, current_lines, sections)
    if sections:
        return tuple(sections)

    text = _clean_text(source.text)
    if not text:
        return ()
    return (
        _RawSection(
            source=source,
            heading_path=(source.title,),
            text=text,
        ),
    )


def _flush_section(
    source: SourceMaterial,
    heading_path: tuple[str, ...] | None,
    current_lines: list[str],
    sections: list[_RawSection],
) -> None:
    text = _clean_text("\n".join(current_lines))
    if not text:
        return
    sections.append(
        _RawSection(
            source=source,
            heading_path=heading_path or (source.title,),
            text=text,
        )
    )


def _parse_heading(line: str) -> tuple[int, str] | None:
    match = _MARKDOWN_HEADING_PATTERN.match(line)
    if match is None:
        return None

    markdown_level = min(len(match.group(1)), 3)
    title = _clean_heading_title(match.group(2))
    if not title:
        return None

    numbered_match = _NUMBERED_HEADING_PATTERN.match(title)
    if numbered_match is not None:
        level = min(numbered_match.group(1).count(".") + 1, 3)
        return level, title

    return markdown_level, title


def _merge_small_sibling_sections(
    sections: Sequence[_RawSection],
) -> tuple[_RawSection, ...]:
    merged: list[_RawSection] = []
    index = 0
    while index < len(sections):
        current = sections[index]
        texts = [current.text]
        start_heading_path = current.heading_path
        total_chars = current.char_count
        next_index = index + 1

        while (
            total_chars < MIN_SEGMENT_CHARS
            and next_index < len(sections)
            and sections[next_index].source.source_id == current.source.source_id
            and sections[next_index].parent_path == current.parent_path
        ):
            sibling = sections[next_index]
            texts.append(sibling.text)
            total_chars += sibling.char_count
            next_index += 1

        merged.append(
            _RawSection(
                source=current.source,
                heading_path=start_heading_path,
                text="\n\n".join(texts),
            )
        )
        index = next_index
    return tuple(merged)


def _split_oversized_text(text: str) -> tuple[tuple[str, str | None], ...]:
    if len(text) <= MAX_SEGMENT_CHARS:
        return ((text, None),)

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    if not paragraphs:
        return ((text[:MAX_SEGMENT_CHARS], "part 1"),)

    chunks: list[tuple[str, str | None]] = []
    current: list[str] = []
    current_chars = 0
    for paragraph in paragraphs:
        paragraph_len = len(paragraph)
        if current and current_chars + paragraph_len + 2 > MAX_SEGMENT_CHARS:
            chunks.append(("\n\n".join(current), f"part {len(chunks) + 1}"))
            current = current[-OVERLAP_PARAGRAPHS:] if OVERLAP_PARAGRAPHS else []
            current_chars = sum(len(item) + 2 for item in current)
        current.append(paragraph)
        current_chars += paragraph_len + 2

    if current:
        chunks.append(("\n\n".join(current), f"part {len(chunks) + 1}"))
    return tuple(chunks)


def _render_location(heading_path: tuple[str, ...], suffix: str | None) -> str:
    location = " > ".join(heading_path)
    if suffix is not None:
        return f"{location} ({suffix})"
    return location


def _clean_heading_title(value: str) -> str:
    value = value.strip().strip("#").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _clean_text(value: str) -> str:
    lines = [line.rstrip() for line in value.splitlines() if not _is_structural_noise(line)]
    text = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def _is_structural_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(_HTML_COMMENT_PATTERN.match(stripped))


def _looks_like_toc_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(re.match(r"^(\d+(?:\.\d+){0,2}\s+.+\s+\.{2,}\s+\d+|.+\s+\.{3,}\s+\d+)$", stripped))
