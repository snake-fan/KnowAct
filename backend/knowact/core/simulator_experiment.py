from datetime import date, datetime
from enum import StrEnum
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.knowact.core.map import MasteryLevel


_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_ENGLISH_MULTI_ASK_PATTERN = re.compile(
    r"\b(?:and|then|also)\s+(?:calculate|choose|compare|describe|diagnose|"
    r"discuss|evaluate|explain|identify|interpret|justify|name|predict|state)\b",
    re.IGNORECASE,
)
_CHINESE_MULTI_ASK_PATTERN = re.compile(
    r"(?:并|然后|同时|再)(?:请)?(?:比较|解释|说明|判断|计算|选择|诊断|识别|解读|"
    r"评估|预测|论证|列出|指出)"
)


class SimulatorExperimentLanguage(StrEnum):
    ENGLISH = "en"
    CHINESE = "zh-CN"


class SimulatorExperimentStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class SimulatorQuestionCognitiveOperation(StrEnum):
    IDENTIFY = "identify"
    EXPLAIN = "explain"
    PREDICT = "predict"
    CALCULATE = "calculate"
    CHOOSE = "choose"
    DIAGNOSE = "diagnose"
    INTERPRET = "interpret"
    COMPARE = "compare"
    EVALUATE = "evaluate"


SimulatorExperimentClientProvider = Literal["openai", "deepseek"]


class BilingualQuestionText(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    en: str
    zh_cn: str

    @field_validator("en", "zh_cn")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    def for_language(self, language: SimulatorExperimentLanguage) -> str:
        if language == SimulatorExperimentLanguage.CHINESE:
            return self.zh_cn
        return self.en


class SimulatorExperimentQuestion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: str
    target_concept: str
    question_type: str
    cognitive_operation: SimulatorQuestionCognitiveOperation
    prompts: BilingualQuestionText
    source_reference_ids: tuple[str, ...] = Field(min_length=1)
    reviewed_target_node_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("question_id")
    @classmethod
    def _question_id_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "question_id")

    @field_validator("target_concept", "question_type")
    @classmethod
    def _values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("source_reference_ids")
    @classmethod
    def _source_reference_ids_must_be_unique_and_safe(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicate source reference ids")
        return tuple(
            _validate_safe_id(source_id, "source_reference_id") for source_id in value
        )

    @field_validator("reviewed_target_node_ids")
    @classmethod
    def _target_node_ids_must_be_unique_and_safe(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicate node ids")
        return tuple(_validate_safe_id(node_id, "reviewed_target_node_id") for node_id in value)

    @model_validator(mode="after")
    def _prompts_must_be_atomic_and_bounded(self):
        _validate_atomic_prompt(
            self.prompts.en,
            field_name="prompts.en",
            terminal_mark="?",
            maximum_length=320,
        )
        _validate_atomic_prompt(
            self.prompts.zh_cn,
            field_name="prompts.zh_cn",
            terminal_mark="？",
            maximum_length=180,
        )
        if len(self.prompts.en.split()) > 55:
            raise ValueError("prompts.en must contain at most 55 words")
        return self


class SimulatorExperimentQuestionBank(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["knowact.simulator_question_bank.v2"] = (
        "knowact.simulator_question_bank.v2"
    )
    bank_id: str
    version: str
    benchmark_domain: str
    title: BilingualQuestionText
    questions: tuple[SimulatorExperimentQuestion, ...] = Field(min_length=20)

    @field_validator("bank_id", "version", "benchmark_domain")
    @classmethod
    def _ids_must_be_safe(cls, value: str, info) -> str:
        return _validate_safe_id(value, info.field_name)

    @field_validator("questions")
    @classmethod
    def _question_ids_must_be_unique(
        cls,
        value: tuple[SimulatorExperimentQuestion, ...],
    ) -> tuple[SimulatorExperimentQuestion, ...]:
        question_ids = [question.question_id for question in value]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("question bank must not contain duplicate question ids")
        return value


class SimulatorQuestionBankSourceReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    title: str
    url: str
    authority: str
    relevance: str
    evidence_used: str
    transfer_limits: str
    decision: Literal["accepted"] = "accepted"

    @field_validator("source_id")
    @classmethod
    def _source_id_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "source_id")

    @field_validator(
        "title",
        "url",
        "authority",
        "relevance",
        "evidence_used",
        "transfer_limits",
    )
    @classmethod
    def _source_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SimulatorQuestionRoleplayReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: str
    role: str
    trial_answer: str
    assessed_mastery_level: MasteryLevel
    cognitive_signal: str
    answer_word_count: int = Field(ge=1, le=45)
    atomicity_pass: Literal[True] = True
    brevity_pass: Literal[True] = True
    cognitive_signal_pass: Literal[True] = True
    bilingual_equivalence_pass: Literal[True] = True
    decision: Literal["accepted"] = "accepted"

    @field_validator("question_id")
    @classmethod
    def _question_id_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "question_id")

    @field_validator("role", "trial_answer", "cognitive_signal")
    @classmethod
    def _review_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def _recorded_word_count_must_match(self):
        if self.answer_word_count != _english_word_count(self.trial_answer):
            raise ValueError("answer_word_count does not match trial_answer")
        return self


class SimulatorQuestionBankQualityReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["knowact.question_bank_quality_review.v1"] = (
        "knowact.question_bank_quality_review.v1"
    )
    bank_id: str
    bank_version: str
    benchmark_domain: str
    bank_content_sha256: str
    review_method_version: Literal["atomic_roleplay_screening_v1"] = (
        "atomic_roleplay_screening_v1"
    )
    screened_at: date
    expert_review_status: Literal["pending"] = "pending"
    sources: tuple[SimulatorQuestionBankSourceReview, ...] = Field(min_length=1)
    question_reviews: tuple[SimulatorQuestionRoleplayReview, ...] = Field(
        min_length=20
    )

    @field_validator("bank_id", "bank_version", "benchmark_domain")
    @classmethod
    def _review_ids_must_be_safe(cls, value: str, info) -> str:
        return _validate_safe_id(value, info.field_name)

    @field_validator("bank_content_sha256")
    @classmethod
    def _hash_must_be_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not re.fullmatch(r"[0-9a-f]{64}", normalized):
            raise ValueError("bank_content_sha256 must be a lowercase SHA-256 digest")
        return normalized

    @field_validator("sources")
    @classmethod
    def _source_ids_must_be_unique(
        cls,
        value: tuple[SimulatorQuestionBankSourceReview, ...],
    ) -> tuple[SimulatorQuestionBankSourceReview, ...]:
        source_ids = [source.source_id for source in value]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("quality review must not contain duplicate source ids")
        return value

    @field_validator("question_reviews")
    @classmethod
    def _review_question_ids_must_be_unique(
        cls,
        value: tuple[SimulatorQuestionRoleplayReview, ...],
    ) -> tuple[SimulatorQuestionRoleplayReview, ...]:
        question_ids = [review.question_id for review in value]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("quality review must not contain duplicate question ids")
        return value


class SimulatorExperimentQuestionBankSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    bank_id: str
    version: str
    benchmark_domain: str
    title: BilingualQuestionText
    question_count: int = Field(ge=0)
    languages: tuple[SimulatorExperimentLanguage, ...] = (
        SimulatorExperimentLanguage.ENGLISH,
        SimulatorExperimentLanguage.CHINESE,
    )


class ParticipantMapStateRevision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    mastery_level: MasteryLevel
    misconceptions: tuple[str, ...]
    unknowns: tuple[str, ...]
    review_note: str | None = None

    @field_validator("node_id")
    @classmethod
    def _node_id_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "node_id")

    @field_validator("misconceptions", "unknowns")
    @classmethod
    def _items_must_not_be_blank_or_duplicated(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("must not contain blank items")
        if len(normalized) != len(set(normalized)):
            raise ValueError("must not contain duplicate items")
        return normalized

    @field_validator("review_note")
    @classmethod
    def _optional_note_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value.strip() if value is not None else None


class SimulatorSelfEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    content_similarity: int = Field(ge=1, le=5)
    knowledge_level_similarity: int = Field(ge=1, le=5)
    boundary_similarity: int = Field(ge=1, le=5)
    style_similarity: int = Field(ge=1, le=5)
    overall_representativeness: int = Field(ge=1, le=5)
    replacement_judgement: Literal[
        "direct_use",
        "minor_bias",
        "major_revision",
        "not_representative",
    ]
    comment: str | None = None

    @field_validator("comment")
    @classmethod
    def _optional_comment_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value.strip() if value is not None else None


class SimulatorExperimentQuestionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: str
    target_concept: str
    question_type: str
    prompts: BilingualQuestionText
    selected_prompt: str
    reviewed_target_node_ids: tuple[str, ...] = Field(default_factory=tuple)
    human_answer: str | None = None
    simulator_answer: str | None = None
    observation_kind: str | None = None
    warning_codes: tuple[str, ...] = Field(default_factory=tuple)
    debug_trace_id: str | None = None
    simulator_error: str | None = None
    self_evaluation: SimulatorSelfEvaluation | None = None
    blind_review_status: Literal["pending"] = "pending"

    @field_validator(
        "selected_prompt",
        "human_answer",
        "simulator_answer",
        "observation_kind",
        "debug_trace_id",
        "simulator_error",
    )
    @classmethod
    def _present_values_must_not_be_blank(cls, value: str | None, info) -> str | None:
        if value is not None and not value.strip():
            raise ValueError(f"{info.field_name} must not be blank")
        return value

    @field_validator("question_id")
    @classmethod
    def _question_id_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "question_id")


class SimulatorExperimentSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["knowact.simulator_test_session.v1"] = (
        "knowact.simulator_test_session.v1"
    )
    session_id: str
    participant_code: str
    status: SimulatorExperimentStatus
    benchmark_domain: str
    graph_version: str
    profile_context_user_id: str
    map_id: str
    question_bank_id: str
    question_bank_version: str
    language: SimulatorExperimentLanguage
    simulator_client_provider: SimulatorExperimentClientProvider
    sampling_seed: int
    question_count: Literal[20] = 20
    questions: tuple[SimulatorExperimentQuestionResult, ...]
    created_at: datetime
    completed_at: datetime | None = None

    @field_validator(
        "session_id",
        "participant_code",
        "benchmark_domain",
        "graph_version",
        "profile_context_user_id",
        "map_id",
        "question_bank_id",
        "question_bank_version",
    )
    @classmethod
    def _ids_must_be_safe(cls, value: str, info) -> str:
        return _validate_safe_id(value, info.field_name)

    @model_validator(mode="after")
    def _session_must_be_internally_consistent(self):
        if len(self.questions) != self.question_count:
            raise ValueError("Simulator experiment session must contain exactly 20 questions")
        question_ids = [question.question_id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Simulator experiment session contains duplicate question ids")
        for question in self.questions:
            if question.selected_prompt != question.prompts.for_language(self.language):
                raise ValueError(
                    f"Question {question.question_id} selected_prompt does not match session language"
                )
        if self.status == SimulatorExperimentStatus.COMPLETED:
            if self.completed_at is None:
                raise ValueError("Completed Simulator experiment session requires completed_at")
            if any(
                question.human_answer is None
                or question.simulator_answer is None
                or question.self_evaluation is None
                for question in self.questions
            ):
                raise ValueError(
                    "Completed Simulator experiment session requires 20 complete answer pairs"
                )
        elif self.completed_at is not None:
            raise ValueError("In-progress Simulator experiment session cannot have completed_at")
        return self


class SimulatorExperimentSessionSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str
    participant_code: str
    status: SimulatorExperimentStatus
    benchmark_domain: str
    map_id: str
    language: SimulatorExperimentLanguage
    answered_questions: int = Field(ge=0)
    evaluated_questions: int = Field(ge=0)
    question_count: int = Field(ge=0)
    created_at: datetime
    completed_at: datetime | None = None


def _validate_atomic_prompt(
    value: str,
    *,
    field_name: str,
    terminal_mark: str,
    maximum_length: int,
) -> None:
    if len(value) > maximum_length:
        raise ValueError(f"{field_name} must contain at most {maximum_length} characters")
    question_mark_count = value.count("?") + value.count("？")
    if question_mark_count != 1:
        raise ValueError(f"{field_name} must contain exactly one question mark")
    if not value.rstrip().endswith(terminal_mark):
        raise ValueError(f"{field_name} must end with {terminal_mark}")
    multi_ask_pattern = (
        _CHINESE_MULTI_ASK_PATTERN
        if field_name.endswith("zh_cn")
        else _ENGLISH_MULTI_ASK_PATTERN
    )
    if multi_ask_pattern.search(value):
        raise ValueError(f"{field_name} must not combine multiple requested operations")


def _english_word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", value))


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} must contain only letters, numbers, dots, underscores, or dashes"
        )
    return value
