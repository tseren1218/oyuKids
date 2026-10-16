"""Create the SingleStore schema and load the seed content.

    OYU_SINGLESTORE_URL=user:pass@host:3306/oyukids python -m scripts.init_db
"""

from pathlib import Path

from app.config import get_settings
from app.db import seed

SCHEMA = Path(__file__).resolve().parents[1] / "app" / "db" / "schema.sql"


def main() -> None:
    import singlestoredb

    url = get_settings().singlestore_url
    if not url:
        raise SystemExit("Set OYU_SINGLESTORE_URL first")

    with singlestoredb.connect(url) as conn, conn.cursor() as cur:
        for statement in filter(str.strip, SCHEMA.read_text().split(";")):
            cur.execute(statement)

        cur.executemany(
            "REPLACE INTO kids (id, name, avatar, grade, streak_days) VALUES (%s, %s, %s, %s, %s)",
            [(k.id, k.name, k.avatar, k.grade, k.streak_days) for k in seed.KIDS],
        )
        cur.executemany(
            "REPLACE INTO passages (id, title, category, level, body, source, emoji) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [(p.id, p.title, p.category, p.level, p.body, p.source, p.emoji) for p in seed.PASSAGES],
        )
        cur.executemany(
            "REPLACE INTO poems (id, title, author, level, body, emoji) VALUES (%s, %s, %s, %s, %s, %s)",
            [(p.id, p.title, p.author, p.level, p.body, p.emoji) for p in seed.POEMS],
        )
        cur.executemany(
            "REPLACE INTO compound_words (id, phrase) VALUES (%s, %s)",
            list(enumerate(seed.COMPOUND_WORDS, start=1)),
        )
        conn.commit()
    print("Schema applied and seed content loaded.")


if __name__ == "__main__":
    main()
