from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    href: str
    icon: str
    color: str
    blurb: str = ""

    def is_active(self, path: str) -> bool:
        return path == "/" if self.href == "/" else path.startswith(self.href)


NAV = (
    NavItem("home", "Нүүр", "/", "🏠", "sun"),
    NavItem("reading", "Хурдан уншлага", "/reading", "📖", "sky", "Чангаар уншаад минутад хэдэн үг уншдагаа мэдээрэй."),
    NavItem("words", "Холбоо үг", "/words", "🧠", "grape", "Үгсийг хараад, цээжлээд, дараа нь хэлээрэй."),
    NavItem("poems", "Шүлэг цээжлэх", "/poems", "📝", "coral", "Шүлгээ алхам алхмаар цээжлээд уншаад өгөөрэй."),
    NavItem("progress", "Миний ахиц", "/progress", "🏆", "mint"),
)
MODULES = NAV[1:4]


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
