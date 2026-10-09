"""The rules engine must give the same, clinically sensible levels for the teaching cases."""
import pytest

from questionnaire import CASES, DEFAULTS, FIELDS, coerce
from rules import assess

LOW, ROUTINE, SOON, URGENT, TODAY = range(5)


def run(**answers):
    r = assess({**DEFAULTS, **answers})
    return r["overall"], {m.id: m for m in r["mods"]}


@pytest.mark.parametrize("key, overall, area, tier", [
    ("A", URGENT, "oral", URGENT),     # white patch in a gutka chewer
    ("B", URGENT, "cervix", URGENT),   # post-coital bleeding
    ("C", URGENT, "lung", URGENT),     # long cough + weight loss in a heavy bidi smoker
    ("D", SOON, "breast", SOON),       # family history, no symptoms
    ("E", ROUTINE, "cervix", ROUTINE), # screened within 5 years
])
def test_example_cases(key, overall, area, tier):
    case = next(c for c in CASES if c["key"] == key)
    got_overall, mods = run(**case["d"])
    assert got_overall == overall
    assert mods[area].tier == tier


def test_apcs_score_matches_published_weights():
    # Yeoh 2011: age 50-69 = 2, male = 1, first-degree relative = 2, smoker = 1 -> 6/7, high risk
    _, mods = run(age=60, sex="male", fhColorectal=True, smoking="past")
    assert mods["bowel"].points == 6
    assert mods["bowel"].tier == SOON


def test_cough_two_weeks_always_prompts_tb_test():
    _, mods = run(age=25, sex="male", cough2w=True)
    assert mods["lung"].tier == SOON
    assert any("TB" in a for a in mods["lung"].actions)


def test_vomiting_blood_is_an_emergency():
    overall, _ = run(age=40, sex="female", vomitBlood=True)
    assert overall == TODAY


def test_women_living_with_hiv_screen_from_25():
    _, mods = run(age=27, sex="female", hiv=True, lastCervicalScreen="within5")
    assert mods["cervix"].tier == SOON


def test_breast_and_cervix_only_for_women():
    _, mods = run(age=45, sex="male")
    assert "breast" not in mods and "cervix" not in mods


def test_young_person_without_risks_is_low():
    overall, _ = run(age=22, sex="male")
    assert overall == LOW


def test_coerce_rejects_values_outside_the_form():
    assert coerce(FIELDS["age"], "52") == 52
    assert coerce(FIELDS["age"], "500") is None
    assert coerce(FIELDS["sex"], "Female") == "female"
    assert coerce(FIELDS["sex"], "other") is None
    assert coerce(FIELDS["mouthPatch"], "true") is True
    assert coerce(FIELDS["mouthPatch"], "false") is None
