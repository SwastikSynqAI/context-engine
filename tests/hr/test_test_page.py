"""Tests for candidate test page helpers."""


def test_answers_to_list_format():
    """Convert {module: {qIndex: optionIndex}} to {module: [optionIndex, ...]}."""
    def answers_to_lists(answers_map, questions):
        result = {}
        for module, qs in questions.items():
            module_answers = []
            for q in qs:
                idx = q["index"]
                selected = answers_map.get(module, {}).get(str(idx))
                module_answers.append(selected if selected is not None else -1)
            result[module] = module_answers
        return result

    questions = {
        "aptitude": [{"index": 0, "question": "Q1", "options": ["A","B","C","D"]},
                     {"index": 1, "question": "Q2", "options": ["A","B","C","D"]}],
        "english":  [{"index": 0, "question": "Q3", "options": ["A","B","C","D"]}],
    }
    answers_map = {"aptitude": {"0": 2, "1": 1}, "english": {"0": 3}}
    result = answers_to_lists(answers_map, questions)
    assert result["aptitude"] == [2, 1]
    assert result["english"] == [3]


def test_unanswered_becomes_minus_one():
    def answers_to_lists(answers_map, questions):
        result = {}
        for module, qs in questions.items():
            module_answers = []
            for q in qs:
                idx = q["index"]
                selected = answers_map.get(module, {}).get(str(idx))
                module_answers.append(selected if selected is not None else -1)
            result[module] = module_answers
        return result

    questions = {"aptitude": [{"index": 0, "question": "Q", "options": []}]}
    result = answers_to_lists({}, questions)
    assert result["aptitude"] == [-1]


def test_module_order_in_test():
    MODULE_ORDER = ["aptitude", "english", "ai"]
    available = {"english": [], "aptitude": [], "ai": []}
    ordered = [m for m in MODULE_ORDER if m in available]
    assert ordered == ["aptitude", "english", "ai"]


def test_timer_seconds_to_mmss():
    def fmt(secs):
        m, s = divmod(secs, 60)
        return f"{m:02d}:{s:02d}"
    assert fmt(2100) == "35:00"
    assert fmt(90) == "01:30"
    assert fmt(0) == "00:00"
