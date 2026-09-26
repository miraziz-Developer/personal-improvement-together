"""The coach's voice: warm, short, specific. Every moment has several phrasings so the
app never sounds like a robot repeating itself. Choice is deterministic per event (seeded),
so a retried job never sends a different text for the same moment."""

import hashlib
from datetime import date

from pit.modules.coaching.domain.messages_ru import LIBRARY_RU, PHRASES_RU, QUOTES_RU
from pit.modules.coaching.domain.moments import (
    Moment as Moment,  # re-exported: callers import it from here
)

STREAK_MILESTONES = frozenset({3, 7, 14, 21, 30, 50, 75, 100})

LIBRARY: dict[Moment, tuple[tuple[str, str], ...]] = {
    Moment.CHALLENGE_STARTED: (
        (
            "Sayohat boshlandi 🚀",
            "{name}, «{title}» boshlandi. Birinchi qadam — eng qiyini, "
            "siz uni allaqachon qo'ydingiz. Oldinda {days} ish kuni.",
        ),
        (
            "Qaror qabul qilindi 💪",
            "Ko'pchilik faqat orzu qiladi, siz esa boshladingiz. «{title}» — {days} ish kuni. "
            "Har kuni bitta qadam, xolos.",
        ),
        (
            "Yangi sahifa ✨",
            "{name}, bugundan yangi odat quryapsiz. Esda tuting: mukammallik emas, "
            "davomiylik muhim.",
        ),
    ),
    Moment.DAY_DONE: (
        ("Bugun — yutuq! ✅", "Zo'r, {name}! Streak: {streak} kun. Ertaga ham shu ruhda!"),
        (
            "Yana bir g'isht qo'yildi 🧱",
            "Har bir bajarilgan kun — kelajakdagi o'zingizga sovg'a. "
            "Streak: {streak}, maqsadgacha {days_left} ish kuni.",
        ),
        (
            "Siz buni uddaladingiz 🔥",
            "{streak} kun ketma-ket! Maqsadga {days_left} ish kuni qoldi.",
        ),
        (
            "Barakalla!",
            "Tomchi-tomchi ko'l bo'lur. Bugungi tomchingiz ham qo'shildi — {streak} kunlik streak.",
        ),
    ),
    Moment.STREAK_MILESTONE: (
        (
            "{streak} kunlik streak! 🏆",
            "{name}, bu endi tasodif emas — bu odat. Siz o'zingizga bergan va'dada turibsiz!",
        ),
        (
            "Yangi cho'qqi: {streak} kun 🔥",
            "Bir paytlar bu qiyin tuyulgan edi. Endi esa bu hayotingizning bir qismi. To'xtamang!",
        ),
        (
            "{streak} kun — faxrlaning! 🌟",
            "{name}, siz {streak} kun davomida o'zingizni tanladingiz. Buni hech kim "
            "sizdan tortib ololmaydi.",
        ),
    ),
    Moment.DAY_FROZEN: (
        (
            "Hech gap yo'q, dam oling 🧊",
            "Bir kun o'tkazib yuborildi, lekin freeze sizni qutqardi — streak saqlandi. "
            "Qolgan freeze: {freezes_left}. Ertaga qaytamiz!",
        ),
        (
            "Hayotda bunday kunlar bo'ladi",
            "{name}, bitta kun hech narsani buzmaydi. Muhimi — ertaga qaytish. "
            "Qolgan freeze: {freezes_left}.",
        ),
    ),
    Moment.CHALLENGE_FAILED: (
        (
            "Bu oxiri emas 🌱",
            "{name}, bu safar chiqmadi — va bu normal. Eng kuchli odamlar ham yiqilgan. "
            "Nima xalaqit berganini o'ylab ko'ring va biroz yengilroq reja bilan qayta boshlang.",
        ),
        (
            "Yiqilish — tajriba",
            "Siz {done} ish kunini bajardingiz — bu bekor ketmadi, odat poydevori qoldi. "
            "Tayyor bo'lsangiz, qaytadan boshlaymiz. Biz yoningizdamiz.",
        ),
    ),
    Moment.CHALLENGE_COMPLETED: (
        (
            "Challenge yakunlandi! 🎉",
            "{name}, siz «{title}»ni oxirigacha yetkazdingiz! Bu — haqiqiy iroda. {money_line}",
        ),
        (
            "G'alaba! 🏆",
            "Barcha kunlar bajarildi. Bu yutuq sizniki — hech kim uni tortib ololmaydi. "
            "{money_line} Keyingi cho'qqi qaysi?",
        ),
    ),
    Moment.PROOF_REJECTED: (
        (
            "Isbot qabul qilinmadi",
            "Sabab: {reason}. Xafa bo'lmang — kun tugaguncha qayta yuborish mumkin. "
            "Siz buni uddalaysiz!",
        ),
        (
            "Yana bir urinish kerak 📸",
            "Tekshiruv natijasi: {reason}. Rasmni aniqroq qilib qayta yuboring — hali vaqt bor!",
        ),
    ),
    Moment.PROOF_IN_REVIEW: (
        (
            "Moderator ko'rib chiqyapti 👀",
            "Isbotingizni inson tekshiradi. Xavotir olmang: faqat AI qarori bilan "
            "hech narsa yo'qolmaydi.",
        ),
    ),
    Moment.MORNING: (
        (
            "Xayrli tong, {name}! ☀️",
            "Bugun {tasks} ta vazifa, jami {minutes} daqiqa. Streak: {streak}. Boshladikmi?",
        ),
        (
            "Yangi kun — yangi imkoniyat",
            "Bugungi reja: {tasks} ta vazifa ({minutes} daqiqa). Kichik qadam ham — qadam.",
        ),
        (
            "Harakatda — barakat 🌅",
            "{name}, bugun {minutes} daqiqa o'zingiz uchun. Bu dunyodagi eng yaxshi sarmoya.",
        ),
    ),
    Moment.REST_DAY: (
        (
            "Bugun dam olish kuni 🌿",
            "Rejangizda bugun vazifa yo'q. Yaxshi dam oling — tiklanish ham mashqning bir qismi.",
        ),
    ),
    Moment.EVENING_REMINDER: (
        (
            "Kun tugashiga oz qoldi ⏰",
            "{name}, bugungi {left} ta vazifa hali kutmoqda. Hozir boshlang — va streak saqlanadi!",
        ),
        (
            "Streakni yo'qotmang 🔥",
            "{streak} kunlik streakingiz sizni kutyapti. Bugungi {left} ta vazifani bajaring — "
            "keyin xotirjam uxlaysiz.",
        ),
    ),
    Moment.FRIEND_DAY_DONE: (
        (
            "{friend} bugungi rejani bajardi 🔥",
            "{friend}ning streak'i — {streak} kun. Siz-chi? Birga kuchliroqmiz 💪",
        ),
        (
            "Do'stingiz oldinda! 🏃",
            "{friend} bugungi vazifalarni yopdi ({streak} kun ketma-ket). Orqada qolmang!",
        ),
        (
            "Jamoa harakatda 🤝",
            "{friend} bugun ham uddaladi. Sizning navbatingiz — bugungi rejani bajaring!",
        ),
    ),
    Moment.WEEKLY_GREAT: (
        (
            "Ajoyib hafta! 🏆",
            "{name}, bu hafta {done}/{planned} kun bajarildi, streak — {streak}. {group_line}"
            "Keyingi haftani ham shunday o'tkazamiz! 💪",
        ),
        (
            "Hafta yakuni: a'lo! 🔥",
            "{done}/{planned} kun — bu intizom. {group_line}O'zingiz bilan faxrlaning, {name}!",
        ),
    ),
    Moment.WEEKLY_OK: (
        (
            "Hafta yakuni 📊",
            "{done}/{planned} kun — yaxshi natija. {group_line}"
            "Keyingi hafta yana bitta kun qo'shsangiz — yangi rekord! 🔥",
        ),
        (
            "Yarim yo'ldan o'tdingiz 💪",
            "{name}, bu hafta {done}/{planned} kun. {group_line}"
            "Dushanba — qaytadan kuchli boshlash uchun eng yaxshi kun.",
        ),
    ),
    Moment.WEEKLY_TOUGH: (
        (
            "Yangi hafta — yangi imkoniyat 🌱",
            "Bu hafta {done}/{planned} kun. Qiyin bo'ldi, bilaman. Lekin siz hali shu yerdasiz — "
            "bu eng muhimi. {group_line}Dushanbadan kichik qadam bilan boshlaymiz.",
        ),
        (
            "Taslim bo'lmaymiz 🤝",
            "{name}, bu hafta {done}/{planned} kun chiqdi. Har bir chempion qiyin haftalarni "
            "boshidan o'tkazgan. {group_line}Ertaga bitta vazifadan boshlang.",
        ),
    ),
    Moment.CHEER: (
        ("{friend} sizni olqishladi {emoji}", "{friend} bugungi natijangizni ko'rdi. Davom eting!"),
        ("{emoji} {friend}dan", "Do'stingiz sizni qo'llab-quvvatlayapti. Bugun ham uddalaysiz!"),
    ),
    Moment.FRIEND_JOINED: (
        (
            "Jamoangiz kattalashdi 👋",
            "{friend} «{title}» guruhingizga qo'shildi. Endi birga harakat qilasizlar!",
        ),
        (
            "Yangi hamroh 🤝",
            "{friend} siz bilan birga «{title}» ni boshladi. Bir-biringizni qo'llab turing!",
        ),
    ),
}

QUOTES: tuple[tuple[str, str], ...] = (
    ("Sabr tagi — sariq oltin.", "O'zbek xalq maqoli"),
    ("Tomchi-tomchi ko'l bo'lur.", "O'zbek xalq maqoli"),
    ("Harakatda — barakat.", "O'zbek xalq maqoli"),
    ("Bugungi ishni ertaga qo'yma.", "O'zbek xalq maqoli"),
    ("Ilm olish — igna bilan quduq qazish.", "O'zbek xalq maqoli"),
    ("Yurgan daryo, o'tirgan bo'yra.", "O'zbek xalq maqoli"),
    ("Motivatsiya boshlaydi, odat davom ettiradi.", "Jim Rayun"),
    ("Mukammal kunni kutma — oddiy kunni mukammal qil.", "PIT"),
    ("Katta natijalar kichik, lekin har kungi qadamlardan tug'iladi.", "PIT"),
    ("Kecha qilolmaganingni bugun qilasan. Shunisi yetarli.", "PIT"),
)


def _index(seed: str, size: int) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest(), 16) % size


PHRASES = {
    "group_line": "Guruhda {rank}-o'rin. ",
    "money_line": "Garovingiz ({stake}) to'liq qaytarildi.",
}

_BY_LOCALE = {
    "uz": (LIBRARY, PHRASES, QUOTES),
    "ru": (LIBRARY_RU, PHRASES_RU, QUOTES_RU),
}


def _derived(phrases: dict[str, str], facts: dict[str, object]) -> dict[str, object]:
    """Sub-sentences that exist only sometimes, in the reader's language."""
    rank, stake = facts.get("rank"), facts.get("stake")
    return {
        "group_line": phrases["group_line"].format(rank=rank) if rank else "",
        "money_line": phrases["money_line"].format(stake=stake) if stake else "",
    }


def compose(moment: Moment, *, seed: str, locale: str = "uz", **facts: object) -> tuple[str, str]:
    library, phrases, _ = _BY_LOCALE.get(locale, _BY_LOCALE["uz"])
    title, body = library[moment][_index(seed, len(library[moment]))]
    values = {**_derived(phrases, facts), **facts}
    return title.format(**values), body.format(**values)


def quote_of_the_day(day: date, locale: str = "uz") -> tuple[str, str]:
    quotes = _BY_LOCALE.get(locale, _BY_LOCALE["uz"])[2]
    return quotes[_index(day.isoformat(), len(quotes))]
