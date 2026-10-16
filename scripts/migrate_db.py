"""Additive, idempotent migration of an existing oyuKids database to the classroom schema.

Never drops tables and never modifies existing rows. Safe to run repeatedly:

  1. creates users / classrooms / memberships / assignments (if missing)
  2. adds a nullable `assignment_id` to attempts and word_rounds (if missing)
  3. copies every row of the legacy `kids` table into `users` as a student with the
     same id (so all attempt history stays linked), with a Latin login name
  4. adds the demo teachers, and — only if no classrooms exist yet — one classroom per
     kids.group_label for the first teacher, with all those students enrolled and a few
     starter assignments that use content present in the database

    python -m scripts.migrate_db             # show the plan, change nothing
    python -m scripts.migrate_db --apply     # do it
"""

import argparse
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from app.config import get_settings
from app.db import seed

SCHEMA = Path(__file__).resolve().parents[1] / "app" / "db" / "schema.sql"
NEW_TABLES = ("users", "classrooms", "memberships", "assignments")

_LATIN = dict(zip(
    "абвгдеёжзийклмноөпрстуүфхцчшщъыьэюя",
    ["a", "b", "v", "g", "d", "e", "yo", "j", "z", "i", "i", "k", "l", "m", "n", "o", "u", "p", "r", "s", "t",
     "u", "u", "f", "kh", "ts", "ch", "sh", "sh", "", "y", "i", "e", "yu", "ya"],
))


def latin_username(name: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z]", "", "".join(_LATIN.get(ch, ch) for ch in name.lower())) or "student"
    username, n = base, 2
    while username in taken:
        username, n = f"{base}{n}", n + 1
    taken.add(username)
    return username


def create_statements() -> dict[str, str]:
    sql = "\n".join(line for line in SCHEMA.read_text().splitlines() if not line.lstrip().startswith("--"))
    statements = {}
    for statement in filter(str.strip, sql.split(";")):
        table = re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", statement).group(1)
        statements[table] = statement
    return statements


def main() -> None:
    import singlestoredb

    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="execute (default: dry run)")
    args = parser.parse_args()

    url = get_settings().singlestore_url
    if not url:
        raise SystemExit("Set OYU_SINGLESTORE_URL first")
    conn = singlestoredb.connect(url, results_type="dicts", autocommit=True)
    cur = conn.cursor()

    def q(sql, params=()):
        cur.execute(sql, params)
        return cur.fetchall()

    def run(label: str, sql: str, params=()):
        print(("  ✔ " if args.apply else "  · ") + label)
        if args.apply:
            cur.execute(sql, params)

    def runmany(label: str, sql: str, rows: list[tuple]):
        print(("  ✔ " if args.apply else "  · ") + f"{label} ({len(rows)} rows)")
        if args.apply and rows:
            cur.executemany(sql, rows)

    tables = {list(r.values())[0] for r in q("SHOW TABLES")}
    columns = lambda t: {r["Field"] for r in q(f"DESCRIBE `{t}`")} if t in tables else set()
    print("Plan" if not args.apply else "Applying")

    # 1. new tables
    statements = create_statements()
    for table in NEW_TABLES:
        if table not in tables:
            run(f"create table {table}", statements[table])

    # 2. new nullable columns
    for table in ("attempts", "word_rounds"):
        if table in tables and "assignment_id" not in columns(table):
            run(f"add column {table}.assignment_id", f"ALTER TABLE {table} ADD COLUMN assignment_id BIGINT NULL")
        elif table not in tables:
            run(f"create table {table}", statements[table])

    users = {r["id"]: r for r in q("SELECT id, username FROM users")} if "users" in tables else {}
    taken = {u["username"] for u in users.values()}

    # 3. legacy kids → student users (same ids)
    if "kids" in tables:
        kids = q("SELECT id, name, avatar, grade, streak_days, created_at FROM kids ORDER BY id")
        rows = [
            (k["id"], "student", latin_username(k["name"], taken), k["name"], k["avatar"], k["grade"], k["streak_days"], k["created_at"])
            for k in kids if k["id"] not in users
        ]
        runmany("copy kids → users (students)", "INSERT INTO users (id, role, username, name, avatar, grade, streak_days, created_at)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", rows)
        for r in rows[:5]:
            print(f"      e.g. {r[3]} → @{r[2]}")

    # 4. teachers + starter classrooms
    teacher_rows = [(t.id, "teacher", t.username, t.name, t.avatar) for t in seed.TEACHERS if t.id not in users]
    runmany("add demo teachers", "INSERT INTO users (id, role, username, name, avatar, created_at) VALUES (%s, %s, %s, %s, %s, NOW())", teacher_rows)

    has_classrooms = "classrooms" in tables and q("SELECT COUNT(*) AS n FROM classrooms")[0]["n"] > 0
    if "kids" in tables and not has_classrooms:
        teacher = seed.TEACHERS[0]
        groups = q("SELECT group_label, MIN(grade) AS grade, COUNT(*) AS n FROM kids GROUP BY group_label ORDER BY group_label")
        passage = q("SELECT id, title FROM passages ORDER BY level, id LIMIT 1")
        poem = q("SELECT id, title FROM poems ORDER BY level, CHAR_LENGTH(body), id LIMIT 1")
        now, today = datetime.now(), date.today()
        for i, g in enumerate(groups, start=1):
            name = f"{int(g['grade'])}-р анги" + (f" ({g['group_label']})" if len(groups) > 1 else "")
            code = f"OYU{int(g['grade'])}{chr(64 + i)}{i}"[:6]
            print(f"  {'✔' if args.apply else '·'} classroom «{name}» for {teacher.name}, code {code}, {g['n']} students")
            if not args.apply:
                continue
            cur.execute("INSERT INTO classrooms (teacher_id, name, grade, emoji, join_code, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                        (teacher.id, name, g["grade"], "🌻", code, now))
            classroom_id = cur.lastrowid
            cur.execute("INSERT INTO memberships (classroom_id, student_id, status, created_at)"
                        " SELECT %s, id, 'active', %s FROM kids WHERE group_label <=> %s", (classroom_id, now, g["group_label"]))
            starter = []
            if passage:
                starter.append(("reading", str(passage[0]["id"]), f"{passage[0]['title']} — чангаар унших", today + timedelta(days=3)))
            if poem:
                starter.append(("poems", str(poem[0]["id"]), f"«{poem[0]['title']}» шүлэг цээжлэх", today + timedelta(days=7)))
            starter.append(("words", "medium", "Холбоо үг · Дунд", today + timedelta(days=2)))
            cur.executemany("INSERT INTO assignments (classroom_id, activity, item_id, title, due_date, instructions, created_at)"
                            " VALUES (%s, %s, %s, %s, %s, '', %s)", [(classroom_id, *a, now) for a in starter])
            print(f"      + {len(starter)} starter assignments: " + ", ".join(a[2] for a in starter))
    elif has_classrooms:
        print("  · classrooms already exist — leaving them alone")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to execute.")
    conn.close()


if __name__ == "__main__":
    main()
