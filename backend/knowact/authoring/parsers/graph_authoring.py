import json
import string

from pydantic import ValidationError

from backend.knowact.authoring.schemas import (
    KnowledgeEdgeList,
    NodeRubricPatch,
    NodeRubricPatchList,
    ReconciledNodeSkeletonDraft,
    ReconciledNodeSkeletonDraftList,
    SegmentNodeExtractionDraftPatch,
    SegmentNodeExtractionDraftPatchList,
    SourceGroundedNodeSkeleton,
    SourceGroundedNodeSkeletonList,
)
from backend.knowact.core.graph import KnowledgeEdge


class AuthoringOutputParseError(RuntimeError):
    """Raised when an authoring agent output cannot be parsed into the expected schema."""


_JSON_CONTROL_ESCAPE_CHARACTERS = frozenset({"b", "f", "n", "r", "t"})
_JSON_HEX_DIGITS = frozenset(string.hexdigits)
_COMMON_LATEX_COMMANDS = frozenset(
    {
        "alpha",
        "argmax",
        "argmin",
        "bar",
        "beta",
        "binom",
        "cdot",
        "chi",
        "delta",
        "dots",
        "epsilon",
        "eta",
        "exp",
        "frac",
        "gamma",
        "geq",
        "hat",
        "infty",
        "kappa",
        "lambda",
        "ldots",
        "leq",
        "ln",
        "log",
        "mathrm",
        "mathbb",
        "mathbf",
        "max",
        "min",
        "mu",
        "nabla",
        "neq",
        "nu",
        "omega",
        "operatorname",
        "partial",
        "phi",
        "pi",
        "prod",
        "psi",
        "rho",
        "sigma",
        "sim",
        "sqrt",
        "sum",
        "tau",
        "text",
        "theta",
        "tilde",
        "times",
        "varphi",
        "xi",
        "zeta",
    }
)


def parse_node_extraction_output(raw_output: str) -> tuple[SourceGroundedNodeSkeleton, ...]:
    return _parse_model(raw_output, SourceGroundedNodeSkeletonList).skeletons


def parse_segment_node_extraction_output(raw_output: str) -> tuple[SegmentNodeExtractionDraftPatch, ...]:
    return _parse_model(raw_output, SegmentNodeExtractionDraftPatchList).drafts


def parse_node_skeleton_reconciliation_output(raw_output: str) -> tuple[ReconciledNodeSkeletonDraft, ...]:
    return _parse_model(raw_output, ReconciledNodeSkeletonDraftList).skeletons


def parse_node_rubric_authoring_output(raw_output: str) -> tuple[NodeRubricPatch, ...]:
    return _parse_model(raw_output, NodeRubricPatchList).nodes


def parse_edge_proposal_output(raw_output: str) -> tuple[KnowledgeEdge, ...]:
    return _parse_model(raw_output, KnowledgeEdgeList).edges


def _parse_model(raw_output: str, model_type):
    try:
        payload = json.loads(_escape_raw_backslashes_in_json_strings(raw_output))
    except json.JSONDecodeError as exc:
        raise AuthoringOutputParseError(
            "Authoring agent output was not valid JSON: "
            f"{exc.msg} at line {exc.lineno} column {exc.colno}"
        ) from exc

    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise AuthoringOutputParseError(
            f"Authoring agent output did not match {model_type.__name__}: {exc}"
        ) from exc


def _escape_raw_backslashes_in_json_strings(raw_output: str) -> str:
    """Escape LLM-copied LaTeX backslashes without changing normal JSON escapes."""
    repaired: list[str] = []
    inside_string = False
    index = 0

    while index < len(raw_output):
        char = raw_output[index]

        if not inside_string:
            repaired.append(char)
            if char == '"':
                inside_string = True
            index += 1
            continue

        if char == '"':
            repaired.append(char)
            inside_string = False
            index += 1
            continue

        if char != "\\":
            repaired.append(char)
            index += 1
            continue

        if index + 1 >= len(raw_output):
            repaired.append("\\\\")
            index += 1
            continue

        next_char = raw_output[index + 1]
        if next_char in {'"', "\\", "/"}:
            repaired.append(char)
            repaired.append(next_char)
            index += 2
            continue

        if next_char == "u":
            if _is_valid_json_unicode_escape(raw_output, index):
                repaired.append(raw_output[index : index + 6])
                index += 6
                continue
            repaired.append("\\\\")
            index += 1
            continue

        if next_char in _JSON_CONTROL_ESCAPE_CHARACTERS:
            command = _alphabetic_word_at(raw_output, index + 1)
            if command in _COMMON_LATEX_COMMANDS:
                repaired.append("\\\\")
                index += 1
                continue
            repaired.append(char)
            repaired.append(next_char)
            index += 2
            continue

        repaired.append("\\\\")
        index += 1

    return "".join(repaired)


def _is_valid_json_unicode_escape(raw_output: str, slash_index: int) -> bool:
    escape_end = slash_index + 6
    if escape_end > len(raw_output):
        return False
    return all(char in _JSON_HEX_DIGITS for char in raw_output[slash_index + 2 : escape_end])


def _alphabetic_word_at(raw_output: str, start_index: int) -> str:
    end_index = start_index
    while end_index < len(raw_output) and raw_output[end_index].isalpha():
        end_index += 1
    return raw_output[start_index:end_index]
