from app.schema import Course, PrepPlan, PrepRow


def test_plan_validates_minimal():
    plan = PrepPlan.model_validate(
        {
            "role": "Data Engineer",
            "rows": [
                {
                    "requirement": "Write SQL",
                    "courses": [
                        {"title": "Intro to SQL", "platform": "Kaggle", "url": "https://example.com"}
                    ],
                }
            ],
        }
    )
    assert plan.role == "Data Engineer"
    assert plan.rows[0].courses[0].title == "Intro to SQL"


def test_course_platform_optional():
    c = Course(title="X", url="https://example.com")
    assert c.platform == ""


def test_nonempty_rows_drops_courseless_rows():
    plan = PrepPlan(
        role="r",
        rows=[
            PrepRow(requirement="has course", courses=[Course(title="a", url="https://a")]),
            PrepRow(requirement="empty", courses=[]),
        ],
    )
    plan.nonempty_rows()
    assert len(plan.rows) == 1
    assert plan.rows[0].requirement == "has course"
