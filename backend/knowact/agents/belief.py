from __future__ import annotations

import math
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


MASTERY_LEVELS = ("L0", "L1", "L2", "L3", "L4", "L5")
_UNIFORM_PROBABILITY = 1.0 / len(MASTERY_LEVELS)


class MasteryLikelihood(BaseModel):
    """Relative likelihood of one visible answer under each mastery level."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    l0: float = Field(ge=0.0, le=1.0)
    l1: float = Field(ge=0.0, le=1.0)
    l2: float = Field(ge=0.0, le=1.0)
    l3: float = Field(ge=0.0, le=1.0)
    l4: float = Field(ge=0.0, le=1.0)
    l5: float = Field(ge=0.0, le=1.0)

    @property
    def values(self) -> tuple[float, ...]:
        return (self.l0, self.l1, self.l2, self.l3, self.l4, self.l5)

    @model_validator(mode="after")
    def _must_have_positive_finite_mass(self) -> Self:
        if not all(math.isfinite(value) for value in self.values):
            raise ValueError("mastery likelihood values must be finite")
        if not any(value > 0.0 for value in self.values):
            raise ValueError("mastery likelihood must contain positive mass")
        return self


class MasteryBelief(BaseModel):
    """Checkpoint-safe marginal distribution over authored L0-L5 levels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    l0: float = Field(ge=0.0, le=1.0)
    l1: float = Field(ge=0.0, le=1.0)
    l2: float = Field(ge=0.0, le=1.0)
    l3: float = Field(ge=0.0, le=1.0)
    l4: float = Field(ge=0.0, le=1.0)
    l5: float = Field(ge=0.0, le=1.0)

    @property
    def values(self) -> tuple[float, ...]:
        return (self.l0, self.l1, self.l2, self.l3, self.l4, self.l5)

    @model_validator(mode="after")
    def _must_be_normalized_and_finite(self) -> Self:
        if not all(math.isfinite(value) for value in self.values):
            raise ValueError("mastery belief values must be finite")
        if not math.isclose(sum(self.values), 1.0, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("mastery belief values must sum to 1")
        return self

    @classmethod
    def uniform(cls) -> Self:
        return cls.from_values((_UNIFORM_PROBABILITY,) * len(MASTERY_LEVELS))

    @classmethod
    def from_values(cls, values: tuple[float, ...]) -> Self:
        if len(values) != len(MASTERY_LEVELS):
            raise ValueError("mastery belief must contain six values")
        total = sum(values)
        if not math.isfinite(total) or total <= 0.0:
            raise ValueError("mastery belief must contain positive finite mass")
        normalized = tuple(value / total for value in values)
        return cls(**dict(zip(_field_names(), normalized, strict=True)))

    @classmethod
    def from_categorical_state(
        cls,
        *,
        assessed_mastery_level: str,
        diagnostic_confidence: str,
    ) -> Self:
        """Recover a conservative prior from a legacy categorical state."""

        if assessed_mastery_level == "unknown":
            return cls.uniform()
        try:
            mode_index = MASTERY_LEVELS.index(assessed_mastery_level)
        except ValueError as exc:
            raise ValueError("unknown assessed mastery level") from exc

        peak_by_confidence = {
            "unknown": 0.34,
            "low": 0.42,
            "medium": 0.60,
            "high": 0.80,
        }
        try:
            peak = peak_by_confidence[diagnostic_confidence]
        except KeyError as exc:
            raise ValueError("unknown diagnostic confidence") from exc
        remainder = (1.0 - peak) / (len(MASTERY_LEVELS) - 1)
        values = [remainder] * len(MASTERY_LEVELS)
        values[mode_index] = peak
        return cls.from_values(tuple(values))

    def bayes_update(
        self,
        likelihood: MasteryLikelihood,
        *,
        probability_floor: float = 1e-6,
    ) -> Self:
        if not 0.0 < probability_floor < 1.0:
            raise ValueError("probability_floor must be between 0 and 1")
        unnormalized = tuple(
            prior * max(observation_likelihood, probability_floor)
            for prior, observation_likelihood in zip(
                self.values,
                likelihood.values,
                strict=True,
            )
        )
        return type(self).from_values(unnormalized)

    @property
    def mode_level(self) -> str:
        mode_index = max(range(len(self.values)), key=self.values.__getitem__)
        return MASTERY_LEVELS[mode_index]

    @property
    def maximum_probability(self) -> float:
        return max(self.values)

    @property
    def normalized_entropy(self) -> float:
        entropy = -sum(
            probability * math.log(probability)
            for probability in self.values
            if probability > 0.0
        )
        return entropy / math.log(len(MASTERY_LEVELS))

    def project(
        self,
        *,
        commitment_threshold: float = 0.35,
    ) -> tuple[str, str]:
        """Project a belief to the legacy mastery/confidence contract."""

        if not 0.0 <= commitment_threshold <= 1.0:
            raise ValueError("commitment_threshold must be between 0 and 1")
        if self.maximum_probability < commitment_threshold:
            return "unknown", "unknown"
        entropy = self.normalized_entropy
        if entropy <= 0.35:
            confidence = "high"
        elif entropy <= 0.65:
            confidence = "medium"
        else:
            confidence = "low"
        return self.mode_level, confidence


def _field_names() -> tuple[str, ...]:
    return ("l0", "l1", "l2", "l3", "l4", "l5")
