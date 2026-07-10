import re
from dataclasses import dataclass
from collections.abc import Sequence

from backend.knowact.authoring.schemas import ParsedSourceSegment, SourceMaterial
from backend.knowact.core.graph import SourceLocator


MIN_SEGMENT_CHARS = 50_000
TARGET_SEGMENT_CHARS = 100_000
MAX_SEGMENT_CHARS = 150_000
OVERLAP_PARAGRAPHS = 0

_MARKDOWN_HEADING_PATTERN = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
_NUMBERED_HEADING_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+){0,2})(?:[\s:.-]+)(.+?)\s*$")
_HTML_COMMENT_PATTERN = re.compile(r"^\s*<!--.*-->\s*$")
_TOC_HEADING_PATTERN = re.compile(r"^(contents|table of contents)\b", re.IGNORECASE)


@dataclass(frozen=True)
class _RawSection:
    source: SourceMaterial
    heading_path: tuple[str, ...]
    text: str
    location: str | None = None

    @property
    def char_count(self) -> int:
        return len(self.text)


def derive_parsed_source_segments(
    source_materials: Sequence[SourceMaterial],
) -> tuple[ParsedSourceSegment, ...]:
    raw_sections: list[_RawSection] = []
    for source in source_materials:
        raw_sections.extend(_pack_adjacent_sections(_parse_source_sections(source)))

    segments: list[ParsedSourceSegment] = []
    next_index = 1
    for section in raw_sections:
        for text, suffix in _split_oversized_text(section.text):
            location = _render_section_location(section, suffix)
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


def _pack_adjacent_sections(
    sections: Sequence[_RawSection],
) -> tuple[_RawSection, ...]:
    groups: list[list[_RawSection]] = []
    current: list[_RawSection] = []
    current_chars = 0

    for section in sections:
        separator_chars = 2 if current else 0
        projected_chars = current_chars + separator_chars + section.char_count
        if current and (
            projected_chars > MAX_SEGMENT_CHARS
            or (
                current_chars >= TARGET_SEGMENT_CHARS
                and projected_chars > TARGET_SEGMENT_CHARS
            )
        ):
            groups.append(current)
            current = []
            current_chars = 0
            separator_chars = 0

        current.append(section)
        current_chars += separator_chars + section.char_count

    if current:
        groups.append(current)

    groups = _merge_short_final_section_group(groups)
    return tuple(_section_group_to_raw_section(group) for group in groups)


def _merge_short_final_section_group(groups: list[list[_RawSection]]) -> list[list[_RawSection]]:
    if len(groups) < 2:
        return groups

    final_group = groups[-1]
    previous_group = groups[-2]
    if (
        _section_group_char_count(final_group) < MIN_SEGMENT_CHARS
        and _section_group_char_count([*previous_group, *final_group]) <= MAX_SEGMENT_CHARS
    ):
        return [*groups[:-2], [*previous_group, *final_group]]
    return groups


def _section_group_to_raw_section(group: Sequence[_RawSection]) -> _RawSection:
    if not group:
        raise ValueError("section group must not be empty")

    source = group[0].source
    heading_path = _common_heading_path([section.heading_path for section in group])
    if not heading_path:
        heading_path = (source.title,)

    start_location = _render_location(group[0].heading_path, None)
    end_location = _render_location(group[-1].heading_path, None)
    location = (
        start_location
        if start_location == end_location
        else f"{start_location} through {end_location}"
    )

    return _RawSection(
        source=source,
        heading_path=heading_path,
        text="\n\n".join(section.text for section in group),
        location=location,
    )


def _section_group_char_count(group: Sequence[_RawSection]) -> int:
    if not group:
        return 0
    return sum(section.char_count for section in group) + (2 * (len(group) - 1))


def _common_heading_path(paths: Sequence[tuple[str, ...]]) -> tuple[str, ...]:
    if not paths:
        return ()

    common: list[str] = []
    for items in zip(*paths):
        first = items[0]
        if any(item != first for item in items):
            break
        common.append(first)
    return tuple(common[:3])


def _split_oversized_text(text: str) -> tuple[tuple[str, str | None], ...]:
    if len(text) <= MAX_SEGMENT_CHARS:
        return ((text, None),)

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    if not paragraphs:
        return _split_plain_text_by_budget(text)

    chunks: list[str] = []
    current: list[str] = []
    current_chars = 0
    for paragraph in paragraphs:
        for piece in _split_paragraph_by_budget(paragraph):
            piece_len = len(piece)
            separator_chars = 2 if current else 0
            projected_chars = current_chars + separator_chars + piece_len

            if current and (
                projected_chars > MAX_SEGMENT_CHARS
                or (
                    current_chars >= TARGET_SEGMENT_CHARS
                    and projected_chars > TARGET_SEGMENT_CHARS
                )
            ):
                chunks.append("\n\n".join(current))
                current = current[-OVERLAP_PARAGRAPHS:] if OVERLAP_PARAGRAPHS else []
                current_chars = sum(len(item) + 2 for item in current)
                separator_chars = 2 if current else 0

            current.append(piece)
            current_chars += separator_chars + piece_len

    if current:
        chunks.append("\n\n".join(current))

    chunks = _merge_short_final_chunk(chunks)
    return tuple((chunk, f"part {index}") for index, chunk in enumerate(chunks, start=1))


def _split_plain_text_by_budget(text: str) -> tuple[tuple[str, str | None], ...]:
    chunks = [
        text[index : index + TARGET_SEGMENT_CHARS]
        for index in range(0, len(text), TARGET_SEGMENT_CHARS)
    ]
    chunks = _merge_short_final_chunk(chunks)
    return tuple((chunk, f"part {index}") for index, chunk in enumerate(chunks, start=1))


def _split_paragraph_by_budget(paragraph: str) -> tuple[str, ...]:
    if len(paragraph) <= MAX_SEGMENT_CHARS:
        return (paragraph,)
    return tuple(
        paragraph[index : index + TARGET_SEGMENT_CHARS]
        for index in range(0, len(paragraph), TARGET_SEGMENT_CHARS)
    )


def _merge_short_final_chunk(chunks: list[str]) -> list[str]:
    if len(chunks) < 2:
        return chunks

    final_chunk = chunks[-1]
    previous_chunk = chunks[-2]
    merged = f"{previous_chunk}\n\n{final_chunk}"
    if len(final_chunk) < MIN_SEGMENT_CHARS and len(merged) <= MAX_SEGMENT_CHARS:
        return [*chunks[:-2], merged]
    return chunks


def _render_location(heading_path: tuple[str, ...], suffix: str | None) -> str:
    location = " > ".join(heading_path)
    if suffix is not None:
        return f"{location} ({suffix})"
    return location


def _render_section_location(section: _RawSection, suffix: str | None) -> str:
    location = section.location or _render_location(section.heading_path, None)
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
