"""Tests for services.asyncapply.agent_dna: every question resolves to
something even with no input, so the composed prompt text is never silent."""

from services.asyncapply.agent_dna import QUESTIONS, questions_payload, render_agent_dna


def test_empty_choices_fall_back_to_every_question_s_default_option():
    text = render_agent_dna(None, None, None)
    for question in QUESTIONS:
        default_instruction = question.options[0].instruction
        assert default_instruction in text


def test_a_chosen_option_s_instruction_replaces_the_default():
    text = render_agent_dna({"tone": "playful"}, None, None)
    playful = next(o for o in next(q for q in QUESTIONS if q.key == "tone").options if o.value == "playful")
    direct_default = next(q for q in QUESTIONS if q.key == "tone").options[0]
    assert playful.instruction in text
    assert direct_default.instruction not in text


def test_an_unrecognized_choice_value_falls_back_to_the_default():
    text = render_agent_dna({"tone": "made-up-value"}, None, None)
    default_instruction = next(q for q in QUESTIONS if q.key == "tone").options[0].instruction
    assert default_instruction in text


def test_notes_are_appended_under_their_own_heading():
    text = render_agent_dna(None, "Always mention I'm open to relocation.", None)
    assert "## Notes" in text
    assert "Always mention I'm open to relocation." in text


def test_blank_notes_add_no_section():
    text = render_agent_dna(None, "   ", None)
    assert "## Notes" not in text


def test_admin_note_is_appended_last_under_its_own_heading():
    text = render_agent_dna(None, "my note", "Never mention salary first.")
    assert text.index("## Notes") < text.index("House rules")
    assert "Never mention salary first." in text


def test_questions_payload_omits_instruction_text():
    payload = questions_payload()
    assert len(payload) == len(QUESTIONS)
    for q in payload:
        assert set(q.keys()) == {"key", "label", "options"}
        for opt in q["options"]:
            assert set(opt.keys()) == {"value", "label"}
