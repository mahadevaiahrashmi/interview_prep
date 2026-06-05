import pytest

from app.generator import (
    GenerationError,
    _repair_json,
    extract_json,
    generate_plan,
    parse_plan,
)

VALID = """```json
{"role": "Dev", "rows": [
  {"requirement": "Write Python", "courses": [{"title": "Py", "platform": "docs", "url": "https://x"}]}
]}
```"""


def test_extract_json_strips_fences():
    out = extract_json(VALID)
    assert out.startswith("{") and out.endswith("}")
    assert "```" not in out


def test_parse_plan_drops_empty_rows():
    raw = (
        '{"role":"r","rows":['
        '{"requirement":"keep","courses":[{"title":"t","url":"https://u"}]},'
        '{"requirement":"drop","courses":[]}'
        "]}"
    )
    plan = parse_plan(raw)
    assert [r.requirement for r in plan.rows] == ["keep"]


def test_repair_json_fixes_trailing_comma_and_quotes():
    broken = '{“role”: "r", "rows": [],}'
    fixed = _repair_json(broken)
    import json

    json.loads(fixed)  # should not raise


def test_generate_plan_empty_jd_raises():
    with pytest.raises(GenerationError):
        generate_plan("   ", provider_name="mock")


def test_generate_plan_with_mock(sample_jd):
    plan = generate_plan(sample_jd, provider_name="mock")
    assert plan.rows
    assert all(r.courses for r in plan.rows)
