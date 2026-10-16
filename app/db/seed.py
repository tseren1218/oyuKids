"""Sample content used by the in-memory mock and by `scripts/init_db.py`.

Passages and the two short poems marked "oyuKids" are original placeholder texts —
swap them for curated essays/novels/quotes/poems before launch.
"""

from datetime import datetime, timedelta

from app.models import Attempt, Kid, Passage, Poem

KIDS = [Kid(id=1, name="Номин", avatar="🦊", grade=3, streak_days=4)]

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


def sample_attempts(kid_id: int = 1) -> list[Attempt]:
    """A few past attempts so the dashboard and progress page aren't empty in the mock."""
    now = datetime.now()
    rows = [
        ("reading", "1", "Говийн хөлөг", 0.92, 2, 58.0, {}, 3),
        ("words", "r-demo-1", "Холбоо үг · Амархан", 1.0, 3, None, {"recalled": 3, "total": 3}, 2),
        ("poems", "1", "Нар", 0.85, 2, None, {}, 2),
        ("reading", "3", "Ном бол мэдлэгийн далай", 0.88, 2, 64.0, {}, 1),
        ("words", "r-demo-2", "Холбоо үг · Дунд", 0.8, 2, None, {"recalled": 4, "total": 5}, 1),
    ]
    return [
        Attempt(
            id=i + 1,
            kid_id=kid_id,
            activity=activity,
            item_id=item_id,
            item_title=title,
            transcript="",
            duration_ms=0,
            score=score,
            stars=stars,
            wpm=wpm,
            details=details,
            created_at=now - timedelta(days=days_ago, hours=i),
        )
        for i, (activity, item_id, title, score, stars, wpm, details, days_ago) in enumerate(rows)
    ]
