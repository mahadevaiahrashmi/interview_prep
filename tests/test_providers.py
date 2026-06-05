import pytest

from app.prompts import build_prompt
from app.providers import ProviderError, get_provider, list_providers
from app.providers.mock import (
    _allocate_windows,
    _is_pure_qualification,
    _parse_timeframe,
    _strip_qualifier,
    build_plan,
)


def test_mock_always_available():
    names = {p["name"]: p for p in list_providers()}
    assert names["mock"]["available"] is True


def test_get_provider_unknown_raises():
    with pytest.raises(ProviderError):
        get_provider("does-not-exist")


def test_pure_qualification_detection():
    # No skill present -> these are pure qualifications and should be droppable.
    assert _is_pure_qualification("Bachelor's degree in Computer Science.", has_skill=False)
    assert _is_pure_qualification("5+ years of professional experience.", has_skill=False)
    # A skill is present -> not a pure qualification (keep the row).
    assert not _is_pure_qualification("5+ years building REST APIs in Python.", has_skill=True)
    # A degree line is dropped even when it name-drops a catalog skill (Statistics).
    assert _is_pure_qualification("Master's degree in Statistics or CS.", has_skill=True)


def test_strip_qualifier_removes_years_clause():
    out = _strip_qualifier("3+ years building REST APIs in Python.")
    assert "year" not in out.lower()
    assert "REST APIs in Python" in out


def test_build_plan_drops_qualifications_and_maps_skills(sample_jd):
    plan = build_plan(sample_jd)
    reqs = [r.requirement for r in plan.rows]
    blob = " || ".join(reqs).lower()

    # Degree / years-only lines are gone.
    assert "bachelor" not in blob
    assert "years of professional experience" not in blob

    # Mixed "years + skill" line survives, with the years clause stripped.
    assert any("rest apis in python" in r.lower() for r in reqs)
    assert "5+ years" not in blob and "3+ years" not in blob

    # Skill lines are mapped to courses.
    assert any("sql" in r.lower() for r in reqs)
    assert plan.role == "Senior Machine Learning Engineer"


def test_build_plan_drops_experience_bar_with_incidental_noun():
    # "4+ years of backend experience" reduces to just "backend" once the years
    # clause is stripped — it's an experience bar, not a skill activity, so drop it.
    plan = build_plan("- 4+ years of backend experience.")
    assert plan.rows == []


def test_build_plan_courses_are_free_links(sample_jd):
    plan = build_plan(sample_jd)
    assert plan.rows, "expected at least one mapped requirement"
    for row in plan.rows:
        assert row.courses, "every kept row must carry at least one course"
        for c in row.courses:
            assert c.url.startswith("https://")
            assert c.title


def test_mock_generate_returns_json(sample_jd):
    raw = get_provider("mock").generate(
        f"=== TARGET JOB DESCRIPTION ===\n{sample_jd}\nRULES — read carefully:\n"
    )
    assert raw.strip().startswith("{")
    assert "rows" in raw


def test_parse_timeframe_reads_common_phrasings():
    assert _parse_timeframe("I have 1 week to prepare")[0] == 7
    assert _parse_timeframe("10 days")[0] == 10
    assert _parse_timeframe("give me a month")[0] == 30
    assert _parse_timeframe("a couple of weeks")[0] == 14
    # No timeframe in the text -> no schedule.
    assert _parse_timeframe("focus on the Python parts") is None


def test_allocate_windows_labels_every_row():
    # More days than rows -> contiguous blocks, one label per row.
    assert len(_allocate_windows(3, 7)) == 3
    # Fewer days than rows -> rows share days, still exactly one label each.
    labels = _allocate_windows(5, 2)
    assert len(labels) == 5
    assert labels[0] == "Day 1" and labels[-1] == "Day 2"
    # No rows -> no labels.
    assert _allocate_windows(0, 5) == []


def test_build_plan_with_timeframe_adds_schedule(sample_jd):
    plan = build_plan(sample_jd, instructions="I have 1 week to prepare")
    assert plan.rows
    assert "week" in plan.guidance.lower()      # pacing summary set
    assert all(r.timebox for r in plan.rows)    # every row gets a study window


def test_build_plan_without_instructions_has_no_schedule(sample_jd):
    # Default behaviour is unchanged: no instructions -> no guidance, no timeboxes.
    plan = build_plan(sample_jd)
    assert plan.guidance == ""
    assert all(r.timebox == "" for r in plan.rows)


def test_build_plan_instructions_without_timeframe_echoes_note(sample_jd):
    plan = build_plan(sample_jd, instructions="focus on the AWS parts")
    assert "focus on the AWS parts" in plan.guidance
    assert all(r.timebox == "" for r in plan.rows)


def test_mock_generate_honors_instructions_in_prompt(sample_jd):
    # Instructions ride along in the built prompt; the mock extracts and applies them.
    prompt = build_prompt(sample_jd, instructions="2 weeks to prepare")
    raw = get_provider("mock").generate(prompt)
    assert '"guidance"' in raw and "timebox" in raw
    assert "week" in raw.lower()
