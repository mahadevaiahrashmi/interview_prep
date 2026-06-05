import pytest

# A job description that mixes learnable skills with pure qualifications, so the
# tests can assert both that skills are mapped and that degree/years bars are
# dropped.
SAMPLE_JD = """Senior Machine Learning Engineer

Responsibilities:
- Build and deploy machine learning models in Python.
- Strong SQL and data warehousing skills.
- Experience with AWS and Docker for production deployment.
- Design scalable system design for low-latency inference.

Requirements:
- Bachelor's degree in Computer Science or a related field.
- 5+ years of professional experience.
- 3+ years building REST APIs in Python.
"""


@pytest.fixture
def sample_jd() -> str:
    return SAMPLE_JD
