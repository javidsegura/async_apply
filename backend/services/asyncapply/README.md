# Careers

Give it job postings, get back a scored evaluation, a tailored CV and cover
letter, and an outreach contact. Everything is stored in this app's own
database.

## The flow

```
POST /api/v1/asyncapply/batches   {"items": ["<url>", "<pasted JD>", ...]}
         │
         │  routers/asyncapply.py writes 1 batch + N items, all "queued",
         │  returns 201 immediately, then hands off to a background task
         ▼
    worker.process_batch()                         ← the entry point
         │  loads the candidate context once, then runs items
         │  `parallelism` at a time (default 2)
         │
         ├──────── item ────────┐  (one per posting, concurrent)
         ▼                      │
  ┌─────────────────────────────┴──────────────────────────────────┐
  │                                                                │
  │  1. extract_jd      URL ──web_fetch / web_search──▶ jd_text    │
  │         ▼           (web_fetch renders JS in real Chromium)    │
  │  2. evaluate_job    jd_text + profile + CV + voice             │
  │         │           ──▶ company, role, score, company_type,    │
  │         │               verdict, strengths, gaps, legitimacy,  │
  │         │               work_auth_tier, hard_stop_reason,      │
  │         │               cv_tailoring (2 projects + tech order),│
  │         │               cover_letter                           │
  │         │           ──▶ SAVED TO DB                            │
  │         │                                                      │
  │         ├── hard stop? ──yes──▶ done, status "hard_stopped"    │
  │         │                                                      │
  │         ▼ no                                                   │
  │  3a. render assets  ──▶ CV + cover letter PDFs (on disk)       │
  │  3b. find_contact   ──WebSearch──▶ name + short message        │
  │         (both best-effort: a failure here is recorded on the   │
  │          item but does not lose the evaluation)                │
  │                                                                │
  └────────────────────────────────────────────────────────────────┘
         │
         ▼
   batch "done" | "partial" (some items failed) | "failed" (all did)
```

Each stage is its own short conversation with a locked-down tool set. The item row is
committed after the evaluation, which is what makes progress pollable and means
a later failure never costs you the scoring.

## API

```
POST   /api/v1/asyncapply/batches            submit postings
GET    /api/v1/asyncapply/batches            all batches
GET    /api/v1/asyncapply/batches/{id}       one batch + live per-item progress
POST   /api/v1/asyncapply/batches/{id}/retry requeue failed items only

GET    /api/v1/asyncapply/items              all evaluated jobs (?status=applied)
PATCH  /api/v1/asyncapply/items/{id}         update application status
GET    /api/v1/asyncapply/items/{id}/cv            download the tailored CV
GET    /api/v1/asyncapply/items/{id}/cover-letter  download the cover letter
```

`status` starts as `evaluated` or `hard_stopped` and is yours to move from
there (`applied`, `interviewing`, `rejected`, ...).

**States.** Items go `queued → running → done | failed`. The batch ends as
`done` (everything worked), `partial` (some items failed) or `failed` (all of
them did). `partial` exists so a single dead link in a batch of twenty is
visible from the batch alone, rather than only by scanning the items. Retry
requeues the failed items whatever the batch state is.

## Layout

```
careers/
├── worker.py          batch + item orchestration, DB state, error handling
├── stages/            the three stages, one file each
│   ├── extract_jd.py
│   ├── evaluate_job.py
│   ├── find_contact.py
│   └── utils/
│       └── outputs.py what each stage returns, as Pydantic models
├── agent/
│   ├── runner.py      the stage loop: call OpenRouter, dispatch tools, parse
│   └── tools/         what the model can call
│       ├── __init__.py    the TOOLS registry and run_tool
│       ├── web_search.py  DuckDuckGo search, and its tool wrapper
│       └── web_fetch.py   Chromium page read, and its tool wrapper
├── utils/             supporting machinery
│   ├── chromium.py    the shared headless-browser launcher
│   └── documents/     making the tailored CV and cover letter
│       ├── html.py    evaluation ──▶ HTML (pure string work)
│       ├── fit.py     trims the CV until it fits cv_max_pages
│       └── pdf.py     HTML ──▶ PDF
├── context/
│   ├── loader.py      reads the files below
│   ├── user/          YOUR files: profile.yml, voice_dna.md (gitignored)
│   ├── modes/         one prompt per stage, same names as stages/
│   └── templates/     the CV and cover-letter HTML
└── settings/
    ├── defaults.yaml  every tunable value
    └── loader.py      defaults.yaml + env overrides
```

`stages/extract_jd.py` ↔ `context/modes/extract_jd.md` — the code and the prompt
for a stage always share a name.

## Setup

1. **Your context.** Put three files in `context/user/` (gitignored, they hold
   personal data). Copy `profile.example.yml` to `profile.yml` to start:
   - `profile.yml` — the single source of truth. Identity, target roles,
     location/work authorization, optional `custom_house_rules` (free-text
     hard stops), and a `cv:` section holding your whole CV. Everything the
     evaluation writes is drawn from here; it never invents experience.
   - `voice_dna.md` — writing style rules for the cover letter.

2. **Your key.** In `backend/.env`:
   ```
   OPENROUTER_API_KEY=sk-or-...
   ```
   That is the only one required: search is keyless.

## Configuration

All defaults live in `settings/defaults.yaml`. Override any of them from
`backend/.env` with `ASYNCAPPLY_<KEY>`:

| Setting | Default | What it does |
|---|---|---|
| `parallelism` | 2 | items processed at once |
| `max_attempts` | 3 | tries per stage before it fails |
| `max_turns` | 8 | tool-call rounds allowed within one try |
| `stage_timeout` | 300 | seconds before one model call is abandoned |
| `fetch_timeout` | 45 | seconds a web_fetch may spend loading a page |
| `cv_max_pages` | 1 | the CV is trimmed until it fits this many pages |
| `output_dir` | `careers/output` | where PDFs are written |

Models are per stage (`ASYNCAPPLY_MODEL_<STAGE>`, or `ASYNCAPPLY_MODEL` for all
three). Extraction is mechanical so it uses a cheap model; evaluation makes the
judgment call and writes the prose, so it gets the better one. Roughly $0.006
per application at the defaults.

If cover letters read generic, that's the one worth upgrading:

```
ASYNCAPPLY_MODEL_EVALUATE_JOB=moonshotai/kimi-k2.5
```

## Notes

- **The model never writes the CV.** Every fact on the page - identity,
  education, experience, projects, awards, activities - comes from
  `profile.yml` verbatim. The model chooses exactly two things: which two
  projects appear, and the order of the technologies list (the ATS signal).
  There is no path by which it can put an employer, a date or a metric on the
  page, so that guarantee needs no prompt and no validation.
- **The CV matches a reference shape.** `fit.py` applies a house style to every
  render - two projects, one education bullet, 17 technologies, four bullets
  per role - so output is consistent rather than a function of how much the
  profile happens to hold.
- **The cover letter is the opposite.** No ATS parses a letter structurally, so
  the model writes three or four paragraphs of free prose. The name, contacts,
  date, company line, greeting and sign-off are all fixed by the template.
- **The CV always fits the page budget.** A static cap does not work here:
  measured on a real profile, cutting technologies from 37 to 20 saves 17px
  while dropping one project saves 78px, and the page was 400px over. So
  `fit.py` renders, measures at the *print* width (measuring at screen width
  under-reports badly, since print wraps far more), and applies the least
  damaging trim it can until the page fits. It never mutates the evaluation
  that was saved to the database.
- **The CV skeleton is fixed, only the tailoring moves.** The layout, your
  identity, education, awards and activities are rendered from `profile.yml`.
  The model decides three things per posting: which jobs and projects lead,
  how each bullet is worded to face this JD, and the order of the technologies
  list. That last one is the main ATS signal, so it is told to use the
  posting's exact spelling wherever your CV means the same thing, and never to
  add a technology you do not claim.
- **The database is the record.** Evaluations live in `asyncapply_items`. PDFs
  are written to `output_dir` and served by the download endpoints; in Docker
  that directory must be a mounted volume or they vanish on rebuild.
- **The agent never touches the filesystem.** `Bash`, `Read`, `Write`, `Edit`
  and `Task` are denied on every stage. PDF rendering is ordinary Python, not an
  agent tool.
- **We call OpenRouter directly** with the `openai` client, since OpenRouter
  speaks the OpenAI chat-completions protocol. `agent/runner.py` owns only the
  tool loop: send messages, dispatch any tool calls, repeat until the model
  answers.
- **Schemas come from Pydantic.** `stages/outputs.py` defines what each stage
  returns; the client turns those models into the JSON schema the provider
  validates against, and hands back a typed object. So `worker.py` reads
  `evaluation.company`, not `evaluation.get("company")`, and a renamed field
  breaks at import rather than silently becoming None.
- **Tools are plain Python functions** under `agent/tools/`. Each tool's module
  holds both halves - what it does, and the wrapper the model sees - so adding
  one means adding a module and a registry line. Argument schemas come from
  Pydantic too. `web_fetch` renders
  the page in Chromium (a real Workday posting returns ~13KB of HTML and zero
  visible text to an ordinary fetch), and `web_search` queries DuckDuckGo with
  no key needed. Note that *scraping* a search page is not an option -
  DuckDuckGo, Bing and Mojeek all block a headless browser - but the ddgs client
  talks to the endpoints behind it and works.
- **Two budgets bound every stage.** `max_turns` caps tool-call rounds within
  one try, `max_attempts` caps retries of the whole stage, and `stage_timeout`
  caps the HTTP call.
- **Chromium presents a normal desktop user agent**, because Playwright's
  default advertises "HeadlessChrome" and some boards degrade it. A posting
  behind a login wall still can't be read: paste the description instead.
- **Job postings are untrusted input.** Every mode prompt treats fetched text as
  data, never instructions.
- **No durable queue.** Batch state is DB rows. If the server dies mid-batch,
  items stuck in `running` stay stuck; nothing resets them on startup.
- **Schema is Alembic-managed.** `asyncapply_batches` / `asyncapply_items` live
  in the AsyncApply database; after editing the models run
  `uv run alembic revision --autogenerate -m "..."` from `backend/`.
