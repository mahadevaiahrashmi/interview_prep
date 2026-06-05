"""Structured representation of the interview-prep plan the LLM must return.

The model is asked to emit JSON matching `PrepPlan`. The renderers
(`render_table`) consume these models, so this schema is the single contract
between the model output and the table the user downloads.

One row per kept job-description sentence; each row lists the FREE courses to
study for that requirement. Sentences that are purely about academic degrees or
years of experience are dropped upstream and never become rows.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Course(BaseModel):
    title: str  # e.g. "Kaggle: Intro to Machine Learning"
    platform: str = ""  # e.g. "Kaggle Learn", "freeCodeCamp", "MIT OCW"
    url: str  # a working link to a FREE course/resource


class PrepRow(BaseModel):
    # `requirement` is one job-description sentence (a skill or responsibility),
    # never a degree or years-of-experience qualification.
    requirement: str
    courses: list[Course] = Field(default_factory=list)
    # Optional study window for this row when the candidate gave a prep timeframe
    # (e.g. "Day 1", "Days 3–4"). Empty when no timeframe was provided.
    timebox: str = ""


class PrepPlan(BaseModel):
    role: str = ""  # the job title inferred from the description
    rows: list[PrepRow] = Field(default_factory=list)
    # One-line pacing summary derived from the candidate's instructions (e.g.
    # "~7 days for 5 requirements — work top to bottom"). Empty when none given.
    guidance: str = ""

    def nonempty_rows(self) -> "PrepPlan":
        """Drop rows that ended up with no courses — an empty row helps no one."""
        self.rows = [r for r in self.rows if r.courses]
        return self
