from backend.knowact.core.simulator_experiment import (
    SimulatorExperimentQuestionBank,
    SimulatorQuestionBankQualityReview,
)


class SimulatorQuestionBankQualityError(ValueError):
    """Raised when a question bank does not match its quality-review artifact."""


def validate_question_bank_quality_review(
    *,
    bank: SimulatorExperimentQuestionBank,
    review: SimulatorQuestionBankQualityReview,
    bank_content_sha256: str,
) -> None:
    errors: list[str] = []
    if review.bank_id != bank.bank_id:
        errors.append("review bank_id does not match question bank")
    if review.bank_version != bank.version:
        errors.append("review bank_version does not match question bank")
    if review.benchmark_domain != bank.benchmark_domain:
        errors.append("review benchmark_domain does not match question bank")
    if review.bank_content_sha256 != bank_content_sha256:
        errors.append("review content hash does not match question bank")

    bank_question_ids = tuple(question.question_id for question in bank.questions)
    review_question_ids = tuple(item.question_id for item in review.question_reviews)
    if set(review_question_ids) != set(bank_question_ids):
        errors.append("review must cover exactly the question ids in the bank")
    if review_question_ids != bank_question_ids:
        errors.append("review question order must match question bank order")

    source_ids = {source.source_id for source in review.sources}
    for question in bank.questions:
        unknown_source_ids = set(question.source_reference_ids) - source_ids
        if unknown_source_ids:
            errors.append(
                f"question {question.question_id} references unknown sources: "
                f"{sorted(unknown_source_ids)}"
            )

    normalized_english_prompts = [
        " ".join(question.prompts.en.lower().split()) for question in bank.questions
    ]
    normalized_chinese_prompts = [
        "".join(question.prompts.zh_cn.split()) for question in bank.questions
    ]
    if len(normalized_english_prompts) != len(set(normalized_english_prompts)):
        errors.append("question bank contains duplicate English prompts")
    if len(normalized_chinese_prompts) != len(set(normalized_chinese_prompts)):
        errors.append("question bank contains duplicate Chinese prompts")

    if errors:
        raise SimulatorQuestionBankQualityError("; ".join(errors))
