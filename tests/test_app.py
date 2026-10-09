"""Smoke-test the Streamlit app headlessly (no API key: Claude features must switch off cleanly)."""
from streamlit.testing.v1 import AppTest


def app():
    at = AppTest.from_file("../streamlit_app.py", default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def page_text(at):
    return " ".join(m.value for m in at.markdown)


def test_opens_on_example_case_a():
    at = app()
    assert "See a doctor within 2 weeks" in page_text(at)


def test_loading_case_e_gives_routine():
    at = app()
    next(b for b in at.button if b.label.startswith("E ·")).click().run()
    assert not at.exception
    assert "Routine screening" in page_text(at)


def test_ticking_a_symptom_changes_the_result():
    at = app()
    next(b for b in at.button if b.label.startswith("E ·")).click().run()
    at.checkbox(key="f_bleedPostcoital").check().run()
    assert not at.exception
    assert "See a doctor within 2 weeks" in page_text(at)


def test_clear_then_shows_prompt():
    at = app()
    next(b for b in at.button if b.label == "Clear all answers").click().run()
    assert not at.exception
    assert any("Enter your age and sex" in i.value for i in at.info)


def test_switching_sex_hides_womens_section():
    at = app()
    next(b for b in at.button if b.label.startswith("B ·")).click().run()
    assert at.checkbox(key="f_earlyMarriage")
    at.radio(key="f_sex").set_value("male").run()
    assert not at.exception
    assert not [c for c in at.checkbox if c.key == "f_earlyMarriage"]


def test_story_fills_form_and_marks_answers(monkeypatch):
    import ai
    monkeypatch.setattr(ai, "make_client", lambda key: object())  # pretend Claude is connected
    monkeypatch.setattr(ai, "read_story", lambda client, text: (
        {"age": 48, "sex": "male", "smokeless": "current", "mouthUlcer": True},
        ["ನೀವು ಧೂಮಪಾನ ಮಾಡುತ್ತೀರಾ?"], "Kannada"))
    at = app()
    at.text_area(key="story").input("ನನಗೆ 48 ವರ್ಷ, ಗುಟ್ಕಾ ತಿನ್ನುತ್ತೇನೆ, ಬಾಯಲ್ಲಿ ಹುಣ್ಣು ಇದೆ").run()
    next(b for b in at.button if b.label == "Read my story").click().run()
    assert not at.exception, at.exception
    assert at.number_input(key="f_age").value == 48
    assert at.checkbox(key="f_mouthUlcer").value is True
    assert at.selectbox(key="lang").value == "Kannada"
    assert "Filled from your story" in page_text(at)
