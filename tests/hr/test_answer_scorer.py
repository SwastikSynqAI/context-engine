"""Unit tests for application answer auto-reject logic."""

def test_blank_answer_is_auto_reject():
    from src.engines.hr.scoring.answer_scorer import score_answer
    result = score_answer("")
    assert result.auto_reject is True
    assert result.rejection_reason == "blank_answer"


def test_none_answer_is_auto_reject():
    from src.engines.hr.scoring.answer_scorer import score_answer
    result = score_answer(None)
    assert result.auto_reject is True


def test_short_answer_under_10_words_is_auto_reject():
    from src.engines.hr.scoring.answer_scorer import score_answer
    result = score_answer("I want this job.")  # 4 words
    assert result.auto_reject is True
    assert result.rejection_reason == "answer_too_short"


def test_exactly_10_words_passes():
    from src.engines.hr.scoring.answer_scorer import score_answer
    result = score_answer("I have five years of solid experience in B2B sales.")  # 10 words
    assert result.auto_reject is False


def test_good_answer_passes():
    from src.engines.hr.scoring.answer_scorer import score_answer
    result = score_answer(
        "I closed a 2 crore deal with a fintech startup by sourcing the "
        "lead on LinkedIn, nurturing for 3 months, and closing with a "
        "custom proposal that addressed their growth stage."
    )
    assert result.auto_reject is False
    assert result.word_count > 30


def test_whitespace_only_answer_is_auto_reject():
    from src.engines.hr.scoring.answer_scorer import score_answer
    result = score_answer("   \n\t  ")
    assert result.auto_reject is True
    assert result.rejection_reason == "blank_answer"


def test_word_count_reported_correctly():
    from src.engines.hr.scoring.answer_scorer import score_answer
    result = score_answer("one two three four five six seven eight nine ten eleven")
    assert result.word_count == 11
