"""Sample content used by the in-memory mock and by `scripts/init_db.py`.

Passages and the two short poems marked "oyuKids" are original placeholder texts —
swap them for curated essays/novels/quotes/poems before launch.
"""

import random
from datetime import date, datetime, timedelta

from app.models import Assignment, Attempt, Classroom, Membership, Passage, Poem, User

TEACHERS = [
    User(id=101, role="teacher", username="sarnai", name="Сарнай багш", avatar="👩‍🏫"),
    User(id=102, role="teacher", username="bat", name="Бат багш", avatar="👨‍🏫"),
]
STUDENTS = [
    User(id=1, role="student", username="nomin", name="Номин", avatar="🦊", grade=3, streak_days=4),
    User(id=2, role="student", username="temuulen", name="Тэмүүлэн", avatar="🐻", grade=3, streak_days=2),
    User(id=3, role="student", username="anujin", name="Анужин", avatar="🐰", grade=3, streak_days=7),
    User(id=4, role="student", username="bilguun", name="Билгүүн", avatar="🐯", grade=3, streak_days=0),
    User(id=5, role="student", username="misheel", name="Мишээл", avatar="🐼", grade=3, streak_days=1),
    User(id=6, role="student", username="khulan", name="Хулан", avatar="🦄", grade=3, streak_days=3),
    User(id=7, role="student", username="ganzorig", name="Ганзориг", avatar="🐸", grade=4, streak_days=0),
    User(id=8, role="student", username="enkhjin", name="Энхжин", avatar="🐨", grade=4, streak_days=5),
]
USERS = TEACHERS + STUDENTS

PASSAGES = [
    Passage(
        id=1,
        title="Говийн хөлөг",
        category="essay",
        level=1,
        emoji="🐫",
        source="oyuKids — жишээ эх",
        body=(
            "Тэмээ бол говийн хөлөг юм. Тэр олон хоног ус уулгүй явж чадна. "
            "Тэмээний бөхөнд өөх хуримтлагддаг. Халуун өдөр ч, хүйтэн шөнө ч тэмээ тэсвэртэй байдаг. "
            "Малчид тэмээгээр ачаа зөөж, ноосоор нь дулаан хувцас хийдэг."
        ),
    ),
    Passage(
        id=2,
        title="Хаврын өглөө",
        category="tale",
        level=1,
        emoji="🌷",
        source="oyuKids — жишээ эх",
        body=(
            "Хаврын нэгэн өглөө Болд эрт сэрлээ. Цонхоор харахад нар гэрэлтэж, шувууд жиргэж байв. "
            "Тэр ээждээ туслахаар гадагш гүйн гарлаа. Хашаанд бяцхан хурга эхийнхээ дэргэд тоглож байлаа. "
            "Болд инээмсэглээд: «Хавар ирлээ!» гэж хашгирав."
        ),
    ),
    Passage(
        id=3,
        title="Ном бол мэдлэгийн далай",
        category="essay",
        level=2,
        emoji="📚",
        source="oyuKids — жишээ эх",
        body=(
            "Ном унших нь бидний оюун ухааныг тэлдэг. Ном бүр шинэ ертөнц рүү хөтлөх хаалга юм. "
            "Өдөр бүр хэдхэн хуудас уншихад л үгийн сан баяжиж, сэтгэн бодох чадвар сайжирна. "
            "Тиймээс номыг хамгийн сайн найз гэж нэрлэдэг."
        ),
    ),
    Passage(
        id=4,
        title="Цасан шуурга",
        category="novel",
        level=2,
        emoji="❄️",
        source="oyuKids — жишээ эх",
        body=(
            "Тэр өвөл цас их орсон. Сүхээ ахтайгаа хамт хонио хашаандаа оруулахаар гарав. "
            "Салхи улам ширүүсч, юу ч харагдахгүй болжээ. Гэтэл тэдний нохой Хасар урд нь гүйж, зам заан хуцав. "
            "Хасарыг дагасаар тэд гэртээ эсэн мэнд хүрч ирлээ."
        ),
    ),
    Passage(
        id=5,
        title="Ардын мэргэн үгс",
        category="quote",
        level=1,
        emoji="💬",
        source="Монгол ардын зүйр цэцэн үг",
        body="Ажил хийвэл ам тосдоно. Эрт босвол нэгийг үзнэ, орой унтвал нэгийг сонсоно. Хичээвэл бүтнэ.",
    ),
    Passage(
        id=6,
        title="Сансрын аялал",
        category="novel",
        level=3,
        emoji="🚀",
        source="oyuKids — жишээ эх",
        body=(
            "Тэмүүлэн шөнө бүр одтой тэнгэр ширтэх дуртай. Нэг өдөр тэр сансрын нисгэгч болохоор шийджээ. "
            "Түүний аав хуучин дуран авчирч, сарны тогоонуудыг үзүүлэв. "
            "«Хичээнгүй сурвал хүсэл чинь заавал биелнэ» гэж аав нь хэлэхэд Тэмүүлэн баяртайгаар толгой дохилоо."
        ),
    ),
]

POEMS = [
    Poem(
        id=1,
        title="Нар",
        author="oyuKids",
        level=1,
        emoji="☀️",
        body="Өглөө нар мандлаа\nӨнгө бүхэн гэрэллээ\nШувуу жиргэн дуулаа\nШинэ өдөр эхэллээ",
    ),
    Poem(
        id=2,
        title="Ээж минь",
        author="oyuKids",
        level=1,
        emoji="💐",
        body="Ээж минь эелдэг\nЭнэрэл нь далай\nӨглөө бүр надад\nӨөдрөг үг хэлнэ",
    ),
    Poem(
        id=3,
        title="Миний нутаг",
        author="Д. Нацагдорж",
        level=3,
        emoji="🏔️",
        body=(
            "Хэнтий, Хангай, Соёны өндөр сайхан нуруунууд\n"
            "Хойд зүгийн чимэг болсон ой хөвч уулнууд\n"
            "Мэнэн, Шарга, Номины өргөн их говиуд\n"
            "Өмнө зүгийн манлай болсон элсэн манхан далайнууд\n"
            "Энэ бол миний төрсөн нутаг\n"
            "Монголын сайхан орон"
        ),
    ),
]

COMPOUND_WORDS = [
    "аав ээж", "ах дүү", "ном дэвтэр", "аяга таваг", "хувцас хунар", "хоол унд",
    "гэр орон", "мал сүрэг", "уул ус", "өдөр шөнө", "найз нөхөд", "зам харгуй",
    "ой мод", "гол мөрөн", "эрдэм ном", "ажил хөдөлмөр", "эрүүл саруул", "сайн сайхан",
    "үг хэл", "салхи шуурга", "цас мөс", "амьтан ургамал", "эд зүйл", "хүүхэд багачууд",
]


_now = datetime.now().replace(second=0, microsecond=0)
_today = date.today()

CLASSROOMS = [
    Classroom(1, 101, "3А анги", 3, "🌻", "OYU3A1", _now - timedelta(days=30)),
    Classroom(2, 101, "Уншлагын дугуйлан", 3, "📚", "READ42", _now - timedelta(days=20)),
    Classroom(3, 102, "4Б анги", 4, "🚀", "STAR4B", _now - timedelta(days=25)),
]
MEMBERSHIPS = (
    [Membership(1, sid, "active", _now - timedelta(days=28)) for sid in (1, 2, 3, 4, 5, 6)]
    + [Membership(1, 7, "invited", _now - timedelta(days=1))]
    + [Membership(2, sid, "active", _now - timedelta(days=18)) for sid in (1, 3, 8)]
    + [Membership(3, sid, "active", _now - timedelta(days=24)) for sid in (7, 8)]
)
ASSIGNMENTS = [
    Assignment(1, 1, "reading", "1", "Говийн хөлөг — чангаар унших", _today + timedelta(days=2), "Тод, чангаар уншаарай.", _now - timedelta(days=3)),
    Assignment(2, 1, "poems", "1", "«Нар» шүлэг цээжлэх", _today + timedelta(days=5), "Эхлээд дасгал хийгээд дараа нь цээжээр хэлээрэй.", _now - timedelta(days=2)),
    Assignment(3, 1, "words", "medium", "Холбоо үг · Дунд", _today - timedelta(days=1), "", _now - timedelta(days=6)),
    Assignment(4, 2, "reading", "3", "Ном бол мэдлэгийн далай", _today + timedelta(days=4), "", _now - timedelta(days=1)),
    Assignment(5, 3, "reading", "4", "Цасан шуурга", _today + timedelta(days=3), "", _now - timedelta(days=2)),
]


def sample_attempts() -> list[Attempt]:
    """Deterministic practice history so dashboards look alive in the mock."""
    rng = random.Random(42)
    titles = {"1": "Говийн хөлөг", "3": "Ном бол мэдлэгийн далай", "4": "Цасан шуурга"}
    rows: list[Attempt] = []

    def add(student_id, assignment, days_ago, score):
        a = assignment
        stars = 3 if score >= 0.95 else 2 if score >= 0.8 else 1 if score >= 0.5 else 0
        wpm = round(rng.uniform(38, 95), 1) if a.activity == "reading" else None
        details = {"recalled": round(score * 5), "total": 5} if a.activity == "words" else {}
        rows.append(
            Attempt(
                student_id=student_id, activity=a.activity, item_id=a.item_id,
                item_title=titles.get(a.item_id, a.title) if a.activity == "reading" else a.title,
                transcript="", duration_ms=rng.randint(20, 60) * 1000, score=score, stars=stars, wpm=wpm,
                details=details, assignment_id=a.id,
                created_at=_now - timedelta(days=days_ago, hours=rng.randint(1, 9)),
            )
        )

    a = {x.id: x for x in ASSIGNMENTS}
    for sid, score in ((1, 0.92), (2, 0.71), (3, 0.97), (5, 0.84)):
        add(sid, a[1], rng.randint(0, 2), score)
    for sid, score in ((1, 0.85), (3, 1.0)):
        add(sid, a[2], rng.randint(0, 1), score)
    for sid, score in ((1, 0.8), (2, 0.6), (3, 1.0), (4, 0.4), (6, 0.9)):
        add(sid, a[3], rng.randint(1, 5), score)
    for sid, score in ((3, 0.94), (8, 0.88)):
        add(sid, a[4], 0, score)
    add(8, a[5], 1, 0.91)
    # free practice (no assignment)
    for sid in (1, 1, 3, 6):
        rows.append(Attempt(sid, "reading", "6", "Сансрын аялал", "", 45000, 0.83, 2, round(rng.uniform(45, 80), 1),
                            created_at=_now - timedelta(days=rng.randint(2, 8))))
    for i, row in enumerate(sorted(rows, key=lambda r: r.created_at), start=1):
        row.id = i
    return rows
