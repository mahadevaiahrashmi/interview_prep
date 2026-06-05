from app.render_table import render_csv, render_html, render_markdown
from app.schema import Course, PrepPlan, PrepRow

PLAN = PrepPlan(
    role="ML Engineer",
    rows=[
        PrepRow(
            requirement="Build models in Python | fast",  # pipe + needs escaping
            courses=[
                Course(title="Intro to ML", platform="Kaggle Learn", url="https://www.kaggle.com/learn/intro-to-machine-learning"),
                Course(title="ML Crash Course", platform="Google", url="https://developers.google.com/machine-learning/crash-course"),
            ],
        ),
    ],
)


def test_markdown_has_table_and_links():
    md = render_markdown(PLAN)
    assert "| # | Requirement | Free courses |" in md
    assert "https://www.kaggle.com/learn/intro-to-machine-learning" in md
    # The pipe inside the requirement must be escaped so the table stays intact.
    assert "Build models in Python \\| fast" in md


def test_csv_flattens_courses():
    csv_out = render_csv(PLAN)
    lines = [ln for ln in csv_out.splitlines() if ln.strip()]
    assert lines[0] == "#,Requirement,Course,Platform,URL"
    # Two courses -> two data rows for the single requirement.
    assert len(lines) == 3
    assert "https://developers.google.com/machine-learning/crash-course" in csv_out


def test_html_escapes_and_links():
    html = render_html(PLAN)
    assert "<table>" in html
    assert 'href="https://www.kaggle.com/learn/intro-to-machine-learning"' in html
    # The raw pipe is fine in HTML, but angle brackets/ampersands would be escaped;
    # confirm the role made it into the title.
    assert "ML Engineer" in html
