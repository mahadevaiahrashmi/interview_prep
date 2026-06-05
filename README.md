# Interview Prep Mapper

Paste a **job description**, pick an AI engine, and get a **table** that maps
every requirement in the posting to the **free courses** you should study to
prepare for the interview — with working links. Download it as **Markdown**,
**CSV**, or a standalone **HTML** page.

> Degree and years-of-experience requirements are intentionally dropped — you
> can't study those away. Only genuinely free courses are listed. When a
> sentence mixes a qualification with a real skill (e.g. *"5+ years building
> REST APIs in Python"*), the qualification is stripped and the skill is kept.

This is a re-spin of
[resume-tailor](https://github.com/mahadevaiahrashmi/resume-tailor): same
FastAPI + multi-engine architecture, different transform (JD → free-course
study plan instead of JD + resume → tailored documents).

---

## Features

- **Five engines, one interface**
  - **Claude CLI** — Anthropic's `claude` CLI (highest quality if you have it).
  - **Gemini CLI** — Google's `gemini` CLI.
  - **Ollama** — fully open-source, runs models like `llama3.1` locally.
  - **OpenRouter** — hosted access to DeepSeek, Qwen, Llama, and more via one
    API key (`OPENROUTER_API_KEY`).
  - **Mock** — offline, no model required. Maps requirements to free courses
    from a built-in catalog so you can preview the table instantly. Always
    available, and what the test suite runs against.
- **Per-engine model picker**, with a **Custom…** box for any model id.
- **One row per requirement**, in the order they appear in the posting.
- **Optional prep timeframe.** Tell it *"1 week"*, *"10 days"*, or *"a month"* and
  each requirement gets a suggested study window (e.g. *Days 1–2*), with a pacing
  summary above the table. Leave it blank for a plain plan.
- **Free-only courses** from stable sources: freeCodeCamp, Kaggle Learn, MIT
  OpenCourseWare, Khan Academy, official docs, Hugging Face, fast.ai, the
  Google/AWS/Microsoft free learning hubs, and more.
- **Three downloads per run:** Markdown (paste into GitHub/Notion), CSV (open in
  Excel/Sheets), HTML (open in a browser or print to PDF).
- **Live table preview** before you download.

## Quickstart

Requires **Python 3.12**.

```bash
cd interview_prep
./run.sh                 # creates .venv, installs deps, starts the server
# open http://127.0.0.1:8000
```

Or manually:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m uvicorn app.main:app --reload
```

Then paste a job description, pick **Mock** (works with zero setup), and click
**Map free courses**.

## Choosing an engine

| Engine     | Setup                                                                 | Where your text goes        |
| ---------- | --------------------------------------------------------------------- | --------------------------- |
| Mock       | none                                                                   | stays on your machine       |
| Ollama     | install from [ollama.com](https://ollama.com), `ollama pull llama3.1` | stays on your machine       |
| Claude CLI | `npm i -g @anthropic-ai/claude-code`, then sign in                    | Anthropic                   |
| Gemini CLI | `npm i -g @google/gemini-cli`, then sign in                           | Google                      |
| OpenRouter | `export OPENROUTER_API_KEY=sk-or-...`                                  | OpenRouter (+ chosen model) |

The Mock and Ollama engines keep everything local; the hosted engines send the
job description to their vendor. This app adds no telemetry and stores no API
keys.

## How it works

```
JD (+ optional timeframe) ──► split into sentences ──► drop degree / years-only
   lines ──► map remaining skills to FREE courses ──► schedule across the
   timeframe ──► PrepPlan (JSON) ──► render Markdown / CSV / HTML table
```

- `app/prompts.py` — the instruction the LLM engines follow (one row per
  sentence, drop qualifications, free links only, honour the prep timeframe).
- `app/providers/` — the five engines behind a common interface.
- `app/providers/mock.py` — the offline catalog, sentence/qualification logic,
  and prep-timeframe scheduling.
- `app/schema.py` — `PrepPlan` / `PrepRow` / `Course`, the contract between
  model output and the rendered table.
- `app/render_table.py` — Markdown / CSV / HTML renderers.
- `app/main.py` — FastAPI routes and file downloads.

## Tests

```bash
./.venv/bin/pytest
```

The suite runs entirely against the offline Mock engine — no network, no API
keys.

## Notes & limits

- Free-course links point at well-known, stable landing pages. Platforms
  occasionally reorganise their catalogs; if a link 404s, search the platform
  for the course title.
- The Mock engine recognises a fixed catalog of common tech skills. A real
  engine will map a wider range of requirements (including soft skills) and
  tailor course choices to the specific role.
- "Free" follows each platform's free tier / free audit / open courseware.
  Paid certificates on otherwise-free courses are out of scope.
