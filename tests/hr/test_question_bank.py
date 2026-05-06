"""Unit tests for pre-screen question bank."""


def test_bd_manager_has_5_questions():
    from src.engines.hr.screening.question_bank import get_questions_for_role
    questions = get_questions_for_role("bd_manager")
    assert len(questions) == 5


def test_operations_manager_has_5_questions():
    from src.engines.hr.screening.question_bank import get_questions_for_role
    questions = get_questions_for_role("operations_manager")
    assert len(questions) == 5


def test_question_has_required_fields():
    from src.engines.hr.screening.question_bank import get_questions_for_role
    questions = get_questions_for_role("bd_manager")
    q = questions[0]
    assert "text" in q
    assert "probe" in q
    assert len(q["text"]) > 20
    assert len(q["probe"]) > 10


def test_unknown_role_returns_generic_questions():
    from src.engines.hr.screening.question_bank import get_questions_for_role
    questions = get_questions_for_role("unknown_role")
    assert len(questions) == 5
    assert all("text" in q and "probe" in q for q in questions)


def test_render_question_email_body():
    from src.engines.hr.screening.question_bank import render_question_email
    body = render_question_email(
        candidate_name="Ananya Sharma",
        question_text="What is the largest B2B deal you have closed?",
        question_number=1,
        total_questions=5,
    )
    assert "Ananya" in body
    assert "1 of 5" in body
    assert "What is the largest B2B deal" in body


def test_render_completion_email():
    from src.engines.hr.screening.question_bank import render_completion_email
    body = render_completion_email(candidate_name="Rahul Gupta")
    assert "Rahul" in body
    assert "received" in body.lower() or "thank" in body.lower()
