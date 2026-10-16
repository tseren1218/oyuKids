"""Set up an EMPTY SingleStore database with the schema and demo data.

    python -m scripts.init_db                    # create missing tables, upsert demo rows
    python -m scripts.init_db --reset --force    # drop every oyuKids table first (destroys data!)

For a database that already has real data, use `python -m scripts.migrate_db` instead.
Reads OYU_SINGLESTORE_URL from the environment / .env.
"""

import argparse
import json
from pathlib import Path

from app.config import get_settings
from app.db import seed

SCHEMA = Path(__file__).resolve().parents[1] / "app" / "db" / "schema.sql"
TABLES = ["attempts", "word_rounds", "assignments", "memberships", "classrooms", "compound_words", "poems", "passages", "users", "kids"]


def main() -> None:
    import singlestoredb

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop all oyuKids tables first")
    parser.add_argument("--force", action="store_true", help="allow --reset / demo upserts on a database that has data")
    args = parser.parse_args()

    url = get_settings().singlestore_url
    if not url:
        raise SystemExit("Set OYU_SINGLESTORE_URL first")

    with singlestoredb.connect(url) as conn, conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        existing = [row[0] for row in cur.fetchall() if row[0] in TABLES]
        if existing and not args.force:
            counts = []
            for table in existing:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts.append(f"{table}={cur.fetchone()[0]}")
            raise SystemExit("Refusing: database already has oyuKids tables (" + ", ".join(counts) + ").\n"
                             "Use `python -m scripts.migrate_db` to upgrade it, or add --force if you really mean to overwrite.")
        if args.reset:
            for table in TABLES:
                cur.execute(f"DROP TABLE IF EXISTS {table}")
        sql = "\n".join(line for line in SCHEMA.read_text().splitlines() if not line.lstrip().startswith("--"))
        for statement in filter(str.strip, sql.split(";")):
            cur.execute(statement)

        def load(table: str, columns: list[str], rows: list[tuple]) -> None:
            placeholders = ", ".join(["%s"] * len(columns))
            cur.executemany(f"REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows)
            print(f"  {table:<15} {len(rows)} rows")

        load("users", ["id", "role", "username", "name", "avatar", "grade", "streak_days"],
             [(u.id, u.role, u.username, u.name, u.avatar, u.grade, u.streak_days) for u in seed.USERS])
        load("passages", ["id", "title", "category", "level", "body", "source", "emoji"],
             [(p.id, p.title, p.category, p.level, p.body, p.source, p.emoji) for p in seed.PASSAGES])
        load("poems", ["id", "title", "author", "level", "body", "emoji"],
             [(p.id, p.title, p.author, p.level, p.body, p.emoji) for p in seed.POEMS])
        load("compound_words", ["id", "phrase"], list(enumerate(seed.COMPOUND_WORDS, start=1)))
        load("classrooms", ["id", "teacher_id", "name", "grade", "emoji", "join_code", "created_at"],
             [(c.id, c.teacher_id, c.name, c.grade, c.emoji, c.join_code, c.created_at) for c in seed.CLASSROOMS])
        load("memberships", ["classroom_id", "student_id", "status", "created_at"],
             [(m.classroom_id, m.student_id, m.status, m.created_at) for m in seed.MEMBERSHIPS])
        load("assignments", ["id", "classroom_id", "activity", "item_id", "title", "due_date", "instructions", "created_at"],
             [(a.id, a.classroom_id, a.activity, a.item_id, a.title, a.due_date, a.instructions, a.created_at) for a in seed.ASSIGNMENTS])
        load("attempts", ["id", "kid_id", "activity", "item_id", "item_title", "transcript", "duration_ms", "score", "stars",
                          "wpm", "details", "assignment_id", "created_at"],
             [(a.id, a.student_id, a.activity, a.item_id, a.item_title, a.transcript, a.duration_ms, a.score, a.stars, a.wpm,
               json.dumps(a.details, ensure_ascii=False), a.assignment_id, a.created_at) for a in seed.sample_attempts()])
        conn.commit()
    print("Schema applied and seed content loaded.")


if __name__ == "__main__":
    main()
