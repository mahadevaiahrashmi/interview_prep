"""Prompt construction for the mapping step.

A single prompt string is built and handed to whichever provider is selected
(Claude / Gemini / Ollama / OpenRouter). Each is instructed to return STRICT
JSON matching the schema in `schema.py`. The generator parses/repairs the
response, but a tight prompt keeps that rare.
"""
from __future__ import annotations

# Shown to the model so it knows the exact JSON shape to emit.
JSON_CONTRACT = """{
  "role": "Job title inferred from the description",
  "guidance": "Optional one-line study-pacing summary; set only when the candidate gave a prep timeframe, else \\"\\".",
  "rows": [
    {
      "requirement": "One job-description sentence describing a skill or responsibility.",
      "timebox": "Optional study window for this row when a timeframe was given (e.g. \\"Day 1\\", \\"Days 3-4\\"), else \\"\\".",
      "courses": [
        {"title": "Course name", "platform": "Provider (e.g. Kaggle Learn)", "url": "https://..."},
        {"title": "Another free course", "platform": "freeCodeCamp", "url": "https://..."}
      ]
    }
  ]
}"""

RULES = """RULES — read carefully:
1. ONE ROW PER SENTENCE: Split the job description into individual sentences /
   bullet points. Each kept sentence becomes exactly one row, in the order it
   appears. Keep the requirement text close to the original wording (lightly
   trimmed is fine).
2. DROP QUALIFICATIONS: Do NOT create rows for sentences that are purely about
   academic degrees (bachelor's, master's, PhD, "degree in ...") or about years
   / length of experience ("5+ years", "minimum 3 years of experience"). You
   cannot study a course to gain a degree or years on the job. If a sentence
   MIXES such a qualification with a concrete skill (e.g. "5+ years building
   REST APIs in Python"), keep the row but rewrite the requirement to the
   learnable skill only ("Building REST APIs in Python").
3. FREE ONLY: Every course MUST be genuinely free to learn from (free tier,
   free audit, open courseware, official docs, or a full free video course).
   Never list a paid course, a paywalled certificate, or a "free trial" that
   later charges. Prefer well-known stable sources: freeCodeCamp, Kaggle Learn,
   MIT OpenCourseWare, Khan Academy, official docs, Google/AWS/Microsoft free
   learning hubs, Hugging Face, fast.ai, The Odin Project.
4. WORKING LINKS: Give a real, working https URL for each course. Prefer the
   course or learning-hub landing page over a guessed deep link. 2-4 courses per
   row, ordered most-relevant first. If you cannot find a free resource for a
   requirement, omit that row rather than inventing a link.
5. FREE-COURSE OUTPUT: Return ONLY a single JSON object matching the schema
   below. No prose, no markdown, no code fences, no comments. Start with { and
   end with }.
6. CANDIDATE INSTRUCTIONS: If a CANDIDATE INSTRUCTIONS section is present, honor
   it. When it states a preparation timeframe (e.g. "1 week", "10 days", "a
   month"), set the top-level "guidance" to a one-line pacing summary and give
   each row a short "timebox" (e.g. "Day 1", "Days 3-4") that schedules the
   requirements, in order, inside that timeframe. If no instructions are given,
   leave "guidance" and every "timebox" as empty strings."""


def build_prompt(jd: str, instructions: str = "") -> str:
    instructions = (instructions or "").strip()
    instructions_block = (
        f"=== CANDIDATE INSTRUCTIONS (honor these) ===\n{instructions}\n\n"
        if instructions
        else ""
    )
    return f"""You are an expert technical interviewer and learning coach. Given a job
description, you build a study plan: for each requirement in the posting you map
the FREE courses a candidate should take to prepare for the interview, and you
return the result as structured JSON for an automated table.

{instructions_block}=== TARGET JOB DESCRIPTION ===
{jd.strip()}

{RULES}

=== JSON SCHEMA (shape to emit; replace the example values) ===
{JSON_CONTRACT}

Now output the study-plan JSON object and nothing else."""
