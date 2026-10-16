from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    href: str
    icon: str
    color: str
    blurb: str = ""
    short: str = ""  # mobile tab bar label

    def is_active(self, path: str) -> bool:
        if self.href in ("/", "/teacher"):
            return path == self.href
        return path.startswith(self.href)


NAV = (
    NavItem("home", "Нүүр", "/", "🏠", "sun", short="Нүүр"),
    NavItem("reading", "Хурдан уншлага", "/reading", "📖", "sky", "Чангаар уншаад минутад хэдэн үг уншдагаа мэдээрэй.", short="Унших"),
    NavItem("words", "Холбоо үг", "/words", "🧠", "grape", "Үгсийг хараад, цээжлээд, дараа нь хэлээрэй.", short="Үг"),
    NavItem("poems", "Шүлэг цээжлэх", "/poems", "📝", "coral", "Шүлгээ алхам алхмаар цээжлээд уншаад өгөөрэй.", short="Шүлэг"),
    NavItem("classes", "Миний анги", "/classes", "🏫", "sun", short="Анги"),
    NavItem("progress", "Миний ахиц", "/progress", "🏆", "mint", short="Ахиц"),
)
MODULES = NAV[1:4]

TEACHER_NAV = (
    NavItem("dashboard", "Хянах самбар", "/teacher", "📊", "sun", short="Самбар"),
    NavItem("classrooms", "Ангиуд", "/teacher/classrooms", "🏫", "sky", short="Ангиуд"),
    NavItem("students", "Сурагчид", "/teacher/students", "🧒", "grape", short="Сурагчид"),
    NavItem("assignments", "Даалгавар", "/teacher/assignments", "📋", "coral", short="Даалгавар"),
)


@dataclass(frozen=True)
class SoonItem:
    slug: str
    label: str
    icon: str
    color: str
    blurb: str


MORE = (
    SoonItem("math", "Сэтгэх тоо", "🔢", "sky", "Цээжээр бодох, тоон таавар"),
    SoonItem("stories", "Үлгэр сонсох", "🎧", "grape", "Унтахын өмнөх аудио үлгэр"),
    SoonItem("english", "Англи хэл", "🔤", "mint", "Шинэ үг, зөв дуудлага"),
    SoonItem("riddles", "Оньсого", "❓", "sun", "Оньсого таагаад оноо ав"),
    SoonItem("drawing", "Зураг зурах", "🎨", "coral", "Өнгө, хэлбэрээр тоглох"),
    SoonItem("logic", "Логик тоглоом", "🧩", "grape", "Эвлүүлэг, дараалал"),
    SoonItem("writing", "Бичих дасгал", "✏️", "sky", "Үсэг, өгүүлбэр бичих"),
    SoonItem("science", "Бяцхан эрдэмтэн", "🔬", "mint", "Сонирхолтой туршилтууд"),
)
MORE_BY_SLUG = {m.slug: m for m in MORE}

ACTIVITIES = {
    "reading": {"icon": "📖", "label": "Уншлага", "color": "sky"},
    "words": {"icon": "🧠", "label": "Холбоо үг", "color": "grape"},
    "poems": {"icon": "📝", "label": "Шүлэг", "color": "coral"},
}
