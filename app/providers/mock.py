"""Deterministic offline provider.

Produces schema-valid JSON from the job description using simple heuristics — no
network, no model. It exists so the app and the test suite run end-to-end without
any CLI or API key installed, and so users can preview the table before wiring up
a real model.

What it does:
  1. Splits the JD into sentences / bullet points.
  2. Drops sentences that are purely academic-degree or years-of-experience
     qualifications (you can't study those away).
  3. For every remaining requirement it scans for known skills and attaches the
     matching FREE courses from `CATALOG` below.

The catalog links are well-known, stable, genuinely-free learning resources.
A real engine (Claude/Gemini/Ollama/OpenRouter) will produce richer, more
targeted mappings; the mock just proves the pipeline and the layout.
"""
from __future__ import annotations

import re

from ..schema import Course, PrepPlan, PrepRow
from .base import LLMProvider

# --- Skill catalog: (compiled keyword pattern, [free courses]) ----------------
# Patterns use word boundaries so short tokens don't match inside other words
# (e.g. "ml" must not fire on "html", "go" must not fire on "going").


def _c(title: str, platform: str, url: str) -> Course:
    return Course(title=title, platform=platform, url=url)


# Order matters: more foundational / common skills first. Each requirement keeps
# the catalog order of whatever it matched, deduped by URL, capped to 4.
_RAW_CATALOG: list[tuple[str, list[Course]]] = [
    (r"\bpython\b", [
        _c("Scientific Computing with Python", "freeCodeCamp", "https://www.freecodecamp.org/learn/scientific-computing-with-python/"),
        _c("Intro to Python", "Kaggle Learn", "https://www.kaggle.com/learn/python"),
        _c("The Python Tutorial", "Official docs", "https://docs.python.org/3/tutorial/"),
    ]),
    (r"\bsql\b|\bdatabases?\b|\bpostgres\b|\bmysql\b", [
        _c("Intro to SQL", "Kaggle Learn", "https://www.kaggle.com/learn/intro-to-sql"),
        _c("Learn SQL", "SQLBolt", "https://sqlbolt.com/"),
        _c("SQL Tutorial", "Mode", "https://mode.com/sql-tutorial/"),
    ]),
    (r"\btypescript\b|\bts\b", [
        _c("The TypeScript Handbook", "Official docs", "https://www.typescriptlang.org/docs/handbook/intro.html"),
    ]),
    (r"\bjavascript\b|\bjs\b|\bes6\b", [
        _c("JavaScript Algorithms and Data Structures", "freeCodeCamp", "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/"),
        _c("The Modern JavaScript Tutorial", "javascript.info", "https://javascript.info/"),
    ]),
    (r"\breact(?:\.js)?\b", [
        _c("Learn React", "react.dev", "https://react.dev/learn"),
        _c("Front End Development Libraries", "freeCodeCamp", "https://www.freecodecamp.org/learn/front-end-development-libraries/"),
    ]),
    (r"\bnode(?:\.js| js)?\b", [
        _c("Learn Node.js", "nodejs.org", "https://nodejs.org/en/learn"),
        _c("Full Stack JavaScript Path", "The Odin Project", "https://www.theodinproject.com/paths/full-stack-javascript"),
    ]),
    (r"\bhtml\b|\bcss\b", [
        _c("Responsive Web Design", "freeCodeCamp", "https://www.freecodecamp.org/learn/2022/responsive-web-design/"),
        _c("Learn CSS", "web.dev", "https://web.dev/learn/css/"),
    ]),
    (r"\bjava\b", [
        _c("Learn Java", "dev.java (Oracle)", "https://dev.java/learn/"),
        _c("Java Programming MOOC", "Univ. of Helsinki", "https://java-programming.mooc.fi/"),
    ]),
    (r"\bgo(?:lang)?\b", [
        _c("A Tour of Go", "go.dev", "https://go.dev/tour/"),
        _c("Get Started with Go", "go.dev", "https://go.dev/learn/"),
    ]),
    (r"c\+\+", [
        _c("Learn C++", "learncpp.com", "https://www.learncpp.com/"),
    ]),
    (r"c#|\.net|asp\.net", [
        _c("Learn .NET", "Microsoft", "https://dotnet.microsoft.com/en-us/learn"),
    ]),
    (r"\brust\b", [
        _c("The Rust Programming Language (book)", "rust-lang.org", "https://doc.rust-lang.org/book/"),
    ]),
    (r"\bdata structures?\b|\balgorithms?\b|\bdsa\b|\bleetcode\b", [
        _c("Introduction to Algorithms (6.006)", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/"),
        _c("DSA Roadmap & Practice", "NeetCode", "https://neetcode.io/"),
    ]),
    (r"\bsystem design\b|\bscalab|\bdistributed systems?\b|\bmicroservices?\b", [
        _c("The System Design Primer", "GitHub", "https://github.com/donnemartin/system-design-primer"),
        _c("Microservices Patterns", "microservices.io", "https://microservices.io/"),
    ]),
    (r"\bdeep learning\b|\bneural net", [
        _c("Intro to Deep Learning", "Kaggle Learn", "https://www.kaggle.com/learn/intro-to-deep-learning"),
        _c("Practical Deep Learning for Coders", "fast.ai", "https://course.fast.ai/"),
    ]),
    (r"\bmachine learning\b|\bml\b|\bscikit|\bsklearn\b", [
        _c("Intro to Machine Learning", "Kaggle Learn", "https://www.kaggle.com/learn/intro-to-machine-learning"),
        _c("Machine Learning Crash Course", "Google", "https://developers.google.com/machine-learning/crash-course"),
        _c("Practical Deep Learning for Coders", "fast.ai", "https://course.fast.ai/"),
    ]),
    (r"\bpandas\b|\bdata wrangling\b|\bdataframes?\b", [
        _c("Pandas", "Kaggle Learn", "https://www.kaggle.com/learn/pandas"),
    ]),
    (r"\bnlp\b|\bnatural language\b", [
        _c("NLP Course", "Hugging Face", "https://huggingface.co/learn/nlp-course"),
    ]),
    (r"\bllm\b|\bgenerative ai\b|\bgenai\b|\brag\b|\bprompt eng", [
        _c("LLM & NLP Courses", "Hugging Face", "https://huggingface.co/learn"),
        _c("Short Courses on GenAI", "DeepLearning.AI", "https://www.deeplearning.ai/short-courses/"),
        _c("Introduction to Generative AI", "Google Cloud Skills Boost", "https://www.cloudskillsboost.google/course_templates/536"),
    ]),
    (r"\bcomputer vision\b|\bopencv\b|\bimage", [
        _c("Computer Vision", "Kaggle Learn", "https://www.kaggle.com/learn/computer-vision"),
    ]),
    (r"\bstatistic|\bprobabilit", [
        _c("Statistics and Probability", "Khan Academy", "https://www.khanacademy.org/math/statistics-probability"),
    ]),
    (r"\baws\b|\bamazon web services\b", [
        _c("AWS Skill Builder (free tier)", "AWS", "https://skillbuilder.aws/"),
        _c("AWS Cloud Practitioner Essentials", "AWS", "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/"),
    ]),
    (r"\bazure\b", [
        _c("Azure Training", "Microsoft Learn", "https://learn.microsoft.com/en-us/training/azure/"),
    ]),
    (r"\bgcp\b|\bgoogle cloud\b", [
        _c("Google Cloud Skills Boost", "Google Cloud", "https://www.cloudskillsboost.google/"),
    ]),
    (r"\bdocker\b|\bcontainers?\b", [
        _c("Get Started with Docker", "Official docs", "https://docs.docker.com/get-started/"),
        _c("Docker for Beginners", "docker-curriculum.com", "https://docker-curriculum.com/"),
    ]),
    (r"\bkubernetes\b|\bk8s\b", [
        _c("Kubernetes Tutorials", "Official docs", "https://kubernetes.io/docs/tutorials/"),
        _c("Kubernetes the Hard Way", "GitHub", "https://github.com/kelseyhightower/kubernetes-the-hard-way"),
    ]),
    (r"\bterraform\b|\binfrastructure as code\b|\biac\b", [
        _c("Terraform Tutorials", "HashiCorp", "https://developer.hashicorp.com/terraform/tutorials"),
    ]),
    (r"\bci/cd\b|continuous (?:integration|delivery|deployment)|\bdevops\b", [
        _c("DevOps Roadmap", "roadmap.sh", "https://roadmap.sh/devops"),
        _c("Learn GitHub Actions", "GitHub Docs", "https://docs.github.com/en/actions/learn-github-actions"),
    ]),
    (r"\bgit\b|\bversion control\b", [
        _c("Learn Git Branching", "interactive", "https://learngitbranching.js.org/"),
        _c("Pro Git (book)", "git-scm", "https://git-scm.com/book/en/v2"),
    ]),
    (r"\blinux\b|\bbash\b|\bshell scripting\b|\bunix\b", [
        _c("Linux Journey", "linuxjourney.com", "https://linuxjourney.com/"),
    ]),
    (r"\brest\b|\bapis?\b|\bbackend\b|\bback[- ]end\b", [
        _c("Back End Development and APIs", "freeCodeCamp", "https://www.freecodecamp.org/learn/back-end-development-and-apis/"),
    ]),
    (r"\bgraphql\b", [
        _c("Introduction to GraphQL", "graphql.org", "https://graphql.org/learn/"),
    ]),
    (r"\bspark\b|\bbig data\b|\bhadoop\b", [
        _c("Apache Spark Quick Start", "Apache", "https://spark.apache.org/docs/latest/quick-start.html"),
    ]),
    (r"\bkafka\b|\bstreaming\b", [
        _c("Apache Kafka 101", "Confluent Developer", "https://developer.confluent.io/courses/"),
    ]),
    (r"\bairflow\b|\borchestration\b", [
        _c("Airflow Tutorial", "Apache", "https://airflow.apache.org/docs/apache-airflow/stable/tutorial/index.html"),
    ]),
    (r"\bpower bi\b", [
        _c("Power BI Training", "Microsoft Learn", "https://learn.microsoft.com/en-us/training/powerplatform/power-bi"),
    ]),
    (r"\btableau\b|\bdata visuali[sz]ation\b|\bdashboards?\b", [
        _c("Data Visualization", "Kaggle Learn", "https://www.kaggle.com/learn/data-visualization"),
    ]),
    (r"\bexcel\b|\bspreadsheets?\b", [
        _c("Excel Tutorials", "Exceljet", "https://exceljet.net/"),
    ]),
    (r"\bagile\b|\bscrum\b|\bkanban\b", [
        _c("Agile & Scrum Resources", "Atlassian", "https://www.atlassian.com/agile"),
    ]),
    (r"\btesting\b|\btdd\b|\bunit tests?\b|\bautomation\b", [
        _c("Test Automation University", "Applitools", "https://testautomationu.applitools.com/"),
    ]),
]

CATALOG: list[tuple[re.Pattern, list[Course]]] = [
    (re.compile(pat, re.I), courses) for pat, courses in _RAW_CATALOG
]

# --- Qualification detection (rows we must NOT create) ------------------------
DEGREE_RE = re.compile(
    r"\b(?:bachelor'?s?|master'?s?|ph\.?\s?d|doctorate|b\.?\s?tech|m\.?\s?tech|"
    r"b\.?\s?e\.?|b\.?\s?sc|m\.?\s?sc|bsc|msc|mba|undergraduate|graduate degree|"
    r"degree (?:in|qualification)|diploma)\b",
    re.I,
)
YEARS_RE = re.compile(
    r"\b\d+\+?\s*(?:to\s*\d+\s*)?years?\b|\byears?\s+of\s+(?:experience|"
    r"professional|relevant|hands[- ]on)|\b(?:minimum|at least)\s+\d+\s*years?",
    re.I,
)

BULLET_RE = re.compile(r"[•●▪‣⁃∙·▪◦‣]")
_LEAD_FILLER = re.compile(r"^(?:and|with|in|the|a|an|of|or|to|using|for|including)\b\s*", re.I)

# --- Prep-timeframe parsing (drives the per-row study schedule) ----------------
_NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "couple": 2, "few": 3,
}
_UNIT_DAYS = {"day": 1, "week": 7, "month": 30}
_TIMEFRAME_RE = re.compile(
    r"\b(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|couple|few)\s*"
    r"(?:of\s+)?(day|week|month)s?\b",
    re.I,
)


def _split_sentences(jd: str) -> list[str]:
    """Break the JD into requirement-sized units: one per bullet or sentence."""
    text = BULLET_RE.sub("\n", jd)
    units: list[str] = []
    for line in text.split("\n"):
        line = line.strip().strip("-–—*•· \t")
        if not line:
            continue
        # Split a multi-sentence line on '.'/';' followed by a capital/number.
        for part in re.split(r"(?<=[.;])\s+(?=[A-Z0-9])", line):
            part = part.strip(" \t-–—*•·")
            if len(part) >= 4:
                units.append(part)
    return units


def _is_pure_qualification(sentence: str, has_skill: bool) -> bool:
    """True when the sentence is a qualification bar we must not turn into a row.

    Degree requirements are always dropped: you can't earn a degree from a free
    course, and the fields they name ("degree in Statistics, CS, ...") are not
    interview skills. A years-of-experience bar is dropped only when it carries
    no learnable skill — a mixed sentence like "5+ years building REST APIs in
    Python" is kept, with the years clause stripped later.
    """
    if DEGREE_RE.search(sentence):
        return True
    if YEARS_RE.search(sentence) and not has_skill:
        return True
    return False


def _strip_qualifier(sentence: str) -> str:
    """Remove degree/years clauses so the requirement reads as a learnable skill."""
    s = YEARS_RE.sub("", sentence)
    s = DEGREE_RE.sub("", s)
    s = re.sub(r"\b(?:of\s+)?(?:professional\s+)?experience\b", "", s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,;:.-–—")
    s = _LEAD_FILLER.sub("", s).strip(" ,;:.-–—")
    return s or sentence


def _courses_for(sentence: str) -> list[Course]:
    """Catalog courses whose keyword appears in the sentence, deduped, capped 4."""
    out: list[Course] = []
    seen: set[str] = set()
    for pattern, courses in CATALOG:
        if pattern.search(sentence):
            for course in courses:
                if course.url not in seen:
                    seen.add(course.url)
                    out.append(course)
    return out[:4]


def _between(text: str, start: str, end: str) -> str:
    try:
        a = text.index(start) + len(start)
        b = text.index(end, a)
        return text[a:b].strip()
    except ValueError:
        return text.strip()


def _infer_role(jd: str) -> str:
    for raw in jd.splitlines():
        line = raw.strip().lstrip("#").strip(" *_`")
        if line:
            return line[:80]
    return "the role"


def _parse_timeframe(text: str) -> tuple[int, str, str] | None:
    """Read a prep horizon from free text -> (total_days, matched_phrase, unit).

    Understands digits and small number-words across day/week/month, e.g.
    "1 week", "10 days", "a month", "couple of weeks". Returns None when no
    timeframe is present (the schedule is then skipped).
    """
    m = _TIMEFRAME_RE.search(text or "")
    if not m:
        return None
    qty_raw, unit = m.group(1).lower(), m.group(2).lower()
    qty = int(qty_raw) if qty_raw.isdigit() else _NUMBER_WORDS.get(qty_raw, 1)
    qty = max(1, min(qty, 365))
    total_days = max(1, min(qty * _UNIT_DAYS[unit], 365))
    return total_days, m.group(0).strip(), unit


def _distribute(total: int, parts: int) -> list[int]:
    """Split `total` into `parts` integers that differ by at most one, front-loaded."""
    base, rem = divmod(total, parts)
    return [base + (1 if i < rem else 0) for i in range(parts)]


def _allocate_windows(n_rows: int, total_days: int) -> list[str]:
    """Schedule `n_rows` requirements across `total_days` -> one label per row.

    When there's at least a day per requirement, each gets a contiguous block
    ("Day 3", "Days 4–5"). When days are scarcer than requirements, several
    requirements share a day.
    """
    if n_rows <= 0:
        return []
    labels: list[str] = []
    if total_days >= n_rows:
        day = 1
        for size in _distribute(total_days, n_rows):
            labels.append(f"Day {day}" if size <= 1 else f"Days {day}–{day + size - 1}")
            day += size
    else:
        day = 1
        for count in _distribute(n_rows, total_days):
            labels.extend(f"Day {day}" for _ in range(count))
            day += 1
    return labels


def _apply_instructions(plan: PrepPlan, instructions: str) -> None:
    """Fold candidate instructions into the plan: pacing guidance + per-row windows."""
    instructions = (instructions or "").strip()
    if not instructions:
        return
    tf = _parse_timeframe(instructions)
    n = len(plan.rows)
    if tf and n:
        total_days, phrase, unit = tf
        for row, label in zip(plan.rows, _allocate_windows(n, total_days)):
            row.timebox = label
        horizon = phrase if unit == "day" else f"{phrase} (~{total_days} days)"
        plan.guidance = (
            f"You have {horizon} to prepare for {n} "
            f"requirement{'s' if n != 1 else ''}. Work top to bottom; "
            f"the suggested study window is shown per row."
        )
    else:
        # No parseable timeframe — echo the note so the user sees it landed. A
        # real engine would actually tailor course choices to it.
        plan.guidance = f"Instructions noted: “{instructions}”."


def build_plan(jd: str, instructions: str = "") -> PrepPlan:
    """Pure JD -> PrepPlan transform, shared by the mock and the tests."""
    rows: list[PrepRow] = []
    for sentence in _split_sentences(jd):
        courses = _courses_for(sentence)
        if not courses:
            continue  # no learnable skill recognised — skip rather than pad
        if _is_pure_qualification(sentence, has_skill=True):
            continue  # a degree bar — always dropped
        if YEARS_RE.search(sentence):
            requirement = _strip_qualifier(sentence)
            # If stripping the years clause leaves only an incidental noun
            # (e.g. "4+ years of backend experience" -> "backend"), it was an
            # experience bar, not a skill activity — drop it.
            if len(requirement.split()) < 2:
                continue
        else:
            requirement = sentence.strip(" .;:")
        rows.append(PrepRow(requirement=requirement, courses=courses))
        if len(rows) >= 40:
            break
    plan = PrepPlan(role=_infer_role(jd), rows=rows)
    _apply_instructions(plan, instructions)
    return plan


class MockProvider(LLMProvider):
    name = "mock"
    label = "Mock (offline preview)"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str) -> str:
        jd = _between(prompt, "=== TARGET JOB DESCRIPTION ===", "RULES — read carefully:")
        instructions = ""
        marker = "=== CANDIDATE INSTRUCTIONS (honor these) ==="
        if marker in prompt:
            instructions = _between(prompt, marker, "=== TARGET JOB DESCRIPTION ===")
        return build_plan(jd, instructions).model_dump_json()
