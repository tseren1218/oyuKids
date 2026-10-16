# oyuKids 🦉

Kids improvement platform — FastAPI + HTMX + SingleStore.

| Module | Flow |
| --- | --- |
| 📖 **Хурдан уншлага** (WPM reading) | Pick a passage → read aloud → STT → word alignment → WPM, accuracy, highlighted mistakes |
| 🧠 **Холбоо үг** (word memorization) | Random холбоо үгс flash for N seconds → hidden → child says them → recall + order score |
| 📝 **Шүлэг цээжлэх** (poem memorization) | Read → progressively hide words (3 levels) → recite → line-by-line accuracy |

## Run

```bash
uv venv && uv pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload
# open http://localhost:8000
.venv/bin/pytest
```

No mic needed: every recorder has a **🎭 Микрофонгүй туршиж үзэх** button that submits an empty clip,
and the mock STT fakes a child's attempt (skips, mispronunciations, mix-ups) from the expected text.

## Accounts & classrooms (mock login)

`/login` → pick **Сурагч** or **Багш**, enter a username (any password) or click a demo account.
A signed `oyu_session` cookie (HMAC, `OYU_SESSION_SECRET`) carries the user id; swap
`app/auth.py:authenticate` for a real check later.

| Demo | Username | Notes |
| --- | --- | --- |
| 👩‍🏫 Сарнай багш | `sarnai` | 3А анги (code `OYU3A1`), Уншлагын дугуйлан (`READ42`) |
| 👨‍🏫 Бат багш | `bat` | 4Б анги (`STAR4B`) |
| 🦊 Номин … 🐨 Энхжин | `nomin`, `temuulen`, `anujin`, `bilguun`, `misheel`, `khulan`, `ganzorig`, `enkhjin` | Ганзориг has a pending invite to 3А |

- **Teacher** (`/teacher`): dashboard (classes, students, open tasks, completion %, upcoming
  deadlines, latest submissions, students needing attention) · classrooms (create, join code,
  invite by username, remove, per-class Students / Assignments / Results matrix) · students ·
  assignments (reading passage, poem, or word-memorization level, with due date) and per-assignment results.
- **Student**: accepts invites or joins with a code (`/classes`); assigned tasks show on the home
  page and open the activity with `?assignment=ID`. An attempt counts toward an assignment only if
  the student is an active member and the item matches.

## Layout

```
app/
  main.py              app factory, routers, auth/STT error handlers
  auth.py              mock login, signed cookie, student_required / teacher_required
  config.py            settings (OYU_* env vars, see .env.example)
  deps.py              get_repo() / get_stt() — picks mock or real backends
  web.py               Jinja templates, role-aware layout context
  navigation.py        student & teacher menus
  models.py            User, Classroom, Membership, Assignment, Attempt, …
  db/
    base.py            Repository protocol
    memory.py          in-memory mock (default)
    singlestore.py     SingleStore implementation (OYU_DB_BACKEND=singlestore)
    schema.sql         tables
    seed.py            demo users, classes, assignments, content, practice history
  services/
    classroom.py       TeacherScope / StudentScope — dashboards from repository data
    stt.py             STT providers (mock, oyu Anir)
    scoring.py         alignment, WPM, poem + word-recall scoring
    practice.py        poem word masking
  routers/             auth, pages, classes, reading, words, poems, teacher
  templates/           base, login, student pages, classes/, teacher/, partials/_ui.html macros
  static/              app.css, recorder.js, htmx.min.js
scripts/init_db.py     apply schema + seed to SingleStore (--reset drops tables)
scripts/try_oyu.py     TTS → STT round trip against oyu
```

## Speech-to-text (Anir by oyu)

Real STT is [oyu's Anir](https://dev.oyu.so): `POST https://api.oyu.so/v1/audio/transcriptions`, multipart
`file`, Bearer key → `{"text", "duration_s"}`. Enable it in `.env`:

```
OYU_STT_PROVIDER=oyu
OYU_STT_API_KEY=sk-...        # https://oyu.so/account/apikeys
```

- Browser recordings (Chrome WebM/Opus, Safari MP4) are accepted as-is — no transcoding.
- `duration_s` from the API is used as the WPM denominator (falls back to the browser timer).
- Output is lowercase, unpunctuated; the scorer normalizes both sides.
- The `model` field is currently ignored by the API (always `auto`).
- Latency is ~2–20 s per clip; the recorder shows a "checking" state meanwhile.
- The 🎭 demo button (empty clip) always uses the mock, even when oyu is enabled. STT failures → HTTP 502 → retry message.
- `python -m scripts.try_oyu` runs a TTS → STT round trip over the seed content and prints accuracy.

## Recordings → S3 (training data)

Every real recording (not the 🎭 demo button) is stored as **16 kHz mono 16-bit PCM WAV** and its
location saved in `attempts.audio_url`, for the lakehouse / oyuLLM:

- The browser converts the MediaRecorder clip to WAV (`recorder.js:toWav`, Web Audio); the same WAV
  goes to Anir and to S3. If conversion fails the original format is stored instead.
- Upload runs concurrently with STT (`services/recording.py`), signed with SigV4 over httpx
  (`services/storage.py`, verified against AWS's published test vector), SSE-S3 encrypted, retried
  on network errors. A storage failure never fails the attempt — `audio_url` stays NULL and it is logged.
- Keys are Hive-partitioned: `s3://oyu-kids-bucket/recordings/activity=reading/date=2026-10-16/student=12/<uuid>.wav`.
  Join with `attempts` (transcript, score, wpm, item) via `audio_url`.
- Teachers can play recordings on the assignment page through a 15-minute presigned link
  (`/teacher/attempts/{id}/audio`, scoped to their own students). The bucket stays private.

```
AWS_ACCESS_KEY_ID=…  AWS_SECRET_ACCESS_KEY=…  AWS_REGION=ap-southeast-1  S3_BUCKET_NAME=oyu-kids-bucket
```

The IAM user needs `s3:PutObject` + `s3:GetObject` (and optionally `s3:DeleteObject`) on
`arn:aws:s3:::oyu-kids-bucket/recordings/*`.

## SingleStore

```
pip install -e '.[singlestore]'
OYU_DB_BACKEND=singlestore
OYU_SINGLESTORE_URL=user:password@host:3306/oyukids
python -m scripts.migrate_db          # existing database: dry run of an additive upgrade
python -m scripts.migrate_db --apply  #   …apply it (never drops or edits existing rows; idempotent)
python -m scripts.init_db             # EMPTY database only: schema + demo data (refuses if data exists)
```

The demo database (`oyu_kids` on demo.novelsoft.mn) was upgraded with `migrate_db`: its 30 legacy
`kids` became student logins with the same ids (Latin usernames, e.g. `amarzayaa`, `tsogttulga`),
Сарнай багш (`sarnai`) owns «5-р анги» (code `OYU5A1`) with all of them, and `attempts`/`word_rounds`
keep the original `kid_id` column. Per-student stats are aggregated in SQL (`student_stats`).

Unique usernames / join codes are enforced in the app (SingleStore unique keys must include the
shard key). One connection per worker thread, reconnecting once on network errors.

Seed passages and the two "oyuKids" poems are placeholders — replace with curated content.
