"""Ready-made challenges for the catalog. Ids are stable (uuid5 of a slug), so seeding twice
never duplicates anything."""

from uuid import NAMESPACE_URL, UUID, uuid5

from pit.catalog_roadmaps import ROADMAPS
from pit.modules.challenges.domain.challenge import Category, Challenge, ProofType, StakePolicy
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec

PHOTO = frozenset({ProofType.PHOTO})
PHOTO_OR_TEXT = frozenset({ProofType.PHOTO, ProofType.TEXT})
MON_TO_SAT = range(6)


def catalog_id(slug: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"pit:challenge:{slug}")


def task(key: str, title: str, minutes: int, *, required: bool = True) -> TaskSpec:
    return TaskSpec(key=key, title=title, minutes=minutes, required=required)


def build_catalog() -> list[Challenge]:
    return [
        Challenge.create_template(
            challenge_id=catalog_id("sport-21"),
            roadmap=ROADMAPS["sport-21"],
            title="21 kunlik sport",
            description="Haftada 6 kun mashq: zal, yugurish yoki uyda. 21 kun — yangi odat "
            "shakllanishining birinchi bosqichi.",
            category=Category.SPORT,
            duration_days=21,
            difficulty=3,
            proof_types=PHOTO,
            verification_prompt="Rasmda mashq qilayotgan foydalanuvchi yoki sport zali, "
            "mashq jihozlari aniq ko'rinsin.",
            stake_policy=StakePolicy(allowed=True),
            default_schedule=Schedule.by_weekday(
                {
                    d: [
                        task("workout", "Mashg'ulot", 45),
                        task("stretch", "Cho'zilish", 10, required=False),
                    ]
                    for d in MON_TO_SAT
                }
            ),
        ),
        Challenge.create_template(
            challenge_id=catalog_id("reading-30"),
            roadmap=ROADMAPS["reading-30"],
            title="Har kuni kitob",
            description="Har kuni kamida 20 bet. Bir oyda 1-2 ta kitob tugaydi — "
            "yil oxirida esa butun bir javon.",
            category=Category.READING,
            duration_days=30,
            difficulty=2,
            proof_types=PHOTO_OR_TEXT,
            verification_prompt="Rasmda ochiq kitob sahifasi ko'rinsin yoki matnda o'qilgan "
            "qism haqida mazmunli xulosa bo'lsin.",
            stake_policy=StakePolicy(allowed=True),
            default_schedule=Schedule.every_day(
                task("read", "20 bet o'qish", 30),
                task("notes", "O'qilganlar xulosasi", 10, required=False),
            ),
        ),
        Challenge.create_template(
            challenge_id=catalog_id("code-30"),
            roadmap=ROADMAPS["code-30"],
            title="30 kunlik kod marafoni",
            description="Haftada 6 kun kod: har kuni yangi mavzu, har hafta — loyihada qo'llash. "
            "Bir oyda portfoliongizga qo'shiladigan ish paydo bo'ladi.",
            category=Category.CODE,
            duration_days=30,
            difficulty=4,
            proof_types=PHOTO_OR_TEXT,
            verification_prompt="Rasmda ekrandagi kod muharriri yoki terminal ko'rinsin "
            "(ekran fotosi), yoki matnda bugun yozilgan kod haqida aniq ma'lumot bo'lsin.",
            stake_policy=StakePolicy(allowed=True),
            default_schedule=Schedule.by_weekday(
                {
                    d: [
                        task("code", "Kod yozish", 65),
                        task("read", "Texnik maqola o'qish", 15, required=False),
                    ]
                    for d in MON_TO_SAT
                }
            ),
        ),
        Challenge.create_template(
            challenge_id=catalog_id("english-30"),
            roadmap=ROADMAPS["english-30"],
            title="Ingliz tili: 30 kun",
            description="Har kuni 10 ta yangi so'z va yangi mavzu, har hafta oxirida — takror. "
            "Oy oxirida 250+ yangi so'z.",
            category=Category.STUDY,
            duration_days=30,
            difficulty=3,
            proof_types=PHOTO_OR_TEXT,
            verification_prompt="Rasmda daftar, darslik yoki o'quv ilovasi ko'rinsin, yoki "
            "matnda o'rganilgan so'zlar va mavzu yozilgan bo'lsin.",
            stake_policy=StakePolicy(allowed=True),
            default_schedule=Schedule.every_day(
                task("words", "10 ta yangi so'z", 15), task("lesson", "Dars", 30)
            ),
        ),
        Challenge.create_template(
            challenge_id=catalog_id("early-21"),
            roadmap=ROADMAPS["early-21"],
            title="Erta turish: 21 kun",
            description="06:30 gacha turish va kunni reja bilan boshlash. Erta tong — "
            "kunning eng samarali soati.",
            category=Category.HEALTH,
            duration_days=21,
            difficulty=2,
            proof_types=PHOTO_OR_TEXT,
            verification_prompt="Rasmda vaqt (soat yoki telefon ekrani) 06:30 dan oldin "
            "ekani yoki yozilgan kun rejasi ko'rinsin.",
            stake_policy=StakePolicy(allowed=True),
            default_schedule=Schedule.every_day(
                task("wake", "06:30 gacha turish", 5),
                task("plan", "Kun rejasini yozish", 10),
            ),
        ),
        Challenge.create_template(
            challenge_id=catalog_id("meditation-14"),
            roadmap=ROADMAPS["meditation-14"],
            title="14 kun ichki xotirjamlik",
            description="Har kuni 10 daqiqa meditatsiya yoki nafas mashqi. Kichik qadam — "
            "katta xotirjamlik.",
            category=Category.HEALTH,
            duration_days=14,
            difficulty=1,
            proof_types=PHOTO_OR_TEXT,
            verification_prompt="Matnda meditatsiya qanday o'tgani yozilsin yoki rasmda "
            "meditatsiya ilovasi natijasi ko'rinsin.",
            stake_policy=StakePolicy(allowed=False),
            default_schedule=Schedule.every_day(task("meditate", "10 daqiqa meditatsiya", 10)),
        ),
        Challenge.create_template(
            challenge_id=catalog_id("steps-30"),
            roadmap=ROADMAPS["steps-30"],
            title="Kuniga 10 000 qadam",
            description="Oddiy, lekin kuchli odat: har kuni 10 000 qadam. Yurak, kayfiyat "
            "va uyqu uchun eng oson sarmoya.",
            category=Category.SPORT,
            duration_days=30,
            difficulty=2,
            proof_types=PHOTO,
            verification_prompt="Rasmda qadam hisoblagich (telefon yoki soat) 10 000 dan "
            "ko'p qadamni ko'rsatsin.",
            stake_policy=StakePolicy(allowed=True),
            default_schedule=Schedule.every_day(task("steps", "10 000 qadam", 60)),
        ),
        Challenge.create_template(
            challenge_id=catalog_id("muaythai-30"),
            roadmap=ROADMAPS["muaythai-30"],
            title="Muay Thai: 30 kun",
            description="Haftada 6 kun: texnika, yugurish va kondisiya navbatma-navbat. Kuch, "
            "chidamlilik va intizom — bir oyda.",
            category=Category.SPORT,
            duration_days=30,
            difficulty=4,
            proof_types=PHOTO,
            verification_prompt="Rasmda Muay Thai / jang san'ati mashg'uloti, bintlangan "
            "qo'llar yoki yugurish jarayoni ko'rinsin.",
            stake_policy=StakePolicy(allowed=True),
            default_schedule=Schedule.by_weekday(
                {d: [task("training", "Mashg'ulot", 70)] for d in MON_TO_SAT}
            ),
        ),
    ]
