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

## Layout

```
app/
  main.py              app factory, router wiring
  config.py            settings (OYU_* env vars, see .env.example)
  deps.py              get_repo() / get_stt() — picks mock or real backends
  web.py               Jinja templates + render helpers
  navigation.py        sidebar menus, "coming soon" modules
  models.py            dataclasses: Kid, Passage, Poem, WordRound, Attempt, KidStats
  db/
    base.py            Repository protocol
    memory.py          in-memory mock (default)
    singlestore.py     SingleStore implementation (OYU_DB_BACKEND=singlestore)
    schema.sql         tables
    seed.py            sample passages, poems, холбоо үгс
  services/
    stt.py             STTProvider protocol, MockSTT, HttpSTT stub  ← plug real API here
    scoring.py         alignment, WPM, poem + word-recall scoring
    practice.py        poem word masking
  routers/             pages, reading, words, poems
  templates/           base layout, partials/_ui.html macros, one folder per module
  static/              app.css, recorder.js (MediaRecorder → upload → htmx swap), htmx.min.js
scripts/init_db.py     apply schema + seed to SingleStore
```

## Going live

- **SingleStore**: `pip install -e '.[singlestore]'`, set `OYU_DB_BACKEND=singlestore` and `OYU_SINGLESTORE_URL`, then `python -m scripts.init_db`.
- **STT**: implement `HttpSTT.transcribe` in `app/services/stt.py` and set `OYU_STT_PROVIDER=http`. The recorder uploads `audio/webm` (Opus) in Chrome/Firefox and `audio/mp4` in Safari.
- Seed passages and the two "oyuKids" poems are placeholders — replace with curated content.
