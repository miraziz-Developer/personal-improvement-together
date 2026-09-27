"""User-facing error messages in other languages.

The domain speaks Uzbek (its messages are the keys); the edges — the API and the Telegram bot —
translate on the way out. A message with no translation falls back to Uzbek, never to nothing.
Templates with values ("Garov {} dan {} gacha...") are matched by pattern."""

import re
from collections.abc import Callable

ERRORS_RU: dict[str, str] = {
    "Kun tartibi hali tuzilmagan": "Распорядок дня ещё не составлен",
    "Bu kun tartibi yangisi bilan almashtirilgan": "Этот распорядок заменён новым",
    "Bu challenge kun tartibida yo'q": "Этого челленджа нет в распорядке",
    "Kun tartibida faqat vazifalar vaqtini o'zgartirish mumkin": "В распорядке можно менять только время задач",
    "Band vaqt uchun kamida bitta hafta kuni tanlang": "Выберите хотя бы один день недели для занятого времени",
    "Bu maqsad rejada yo'q": "Такой цели нет в плане",
    "Hamma maqsadlar birga boshlanadi": "Все цели начинаются вместе",
    "Har bir maqsad uchun reja bo'lishi kerak": "Для каждой цели нужен план",
    "Har bir maqsadni yozing": "Напишите каждую цель",
    "Kun tartibingizda bu maqsad uchun bo'sh vaqt qolmadi": "В вашем распорядке не осталось свободного времени для этой цели",
    "Muddat 30, 60 yoki 90 kun bo'lsin": "Срок — 30, 60 или 90 дней",
    "Uyg'onish va uxlash vaqti orasida kamida 6 soat bo'lsin (uxlash yarim tungacha)": "Между подъёмом и сном должно быть не меньше 6 часов (отбой — до полуночи)",
    "Faqat katalog challenge'i yangilanadi": "Обновлять можно только челленджи каталога",
    "Haftada 7 tadan ortiq dars bo'lmaydi": "В неделе не больше 7 уроков",
    "AI ishonch darajasi 0 va 1 oralig'ida bo'lishi kerak": "Уверенность ИИ должна быть от 0 до 1",
    "AI uchun tekshiruv mezoni yozilishi kerak": "Нужно описать критерий проверки для ИИ",
    "Akkaunt allaqachon o'chirilgan": "Аккаунт уже удалён",
    "Akkaunt o'chirilgan": "Аккаунт удалён",
    "Avval Telegram'ni ulang": "Сначала подключите Telegram",
    "Bo'sh vaqt 7 kun uchun ko'rsatilishi kerak": "Укажите свободное время на все 7 дней",
    "Bo'sh vaqt juda kam: kamida bir kunga 20 daqiqa ajrating": "Слишком мало свободного времени: выделите хотя бы 20 минут в один из дней",
    "Boshlangan rejani challenge sahifasida o'zgartiring": "Начатый план меняется на странице челленджа",
    "Bu Google akkaunt allaqachon ro'yxatdan o'tgan. Kirish'ni bosing": "Этот Google-аккаунт уже зарегистрирован. Нажмите «Войти»",
    "Bu bo'lim faqat moderatorlar uchun": "Этот раздел только для модераторов",
    "Bu challenge allaqachon boshqa guruhda": "Этот челлендж уже в другой группе",
    "Bu challenge guruhda emas": "Этот челлендж не в группе",
    "Bu challenge rad etilgan": "Этот челлендж отклонён",
    "Bu challenge'da pul qo'yish rejimi yo'q": "В этом челлендже нет режима ставок",
    "Bu foydalanuvchi guruhingizda emas": "Этого пользователя нет в вашей группе",
    "Bu reja allaqachon boshlangan": "Этот план уже начат",
    "Bu shaxsiy challenge — unga faqat taklif havolasi orqali qo'shilish mumkin": "Это личный челлендж — присоединиться можно только по ссылке-приглашению",
    "Bu shikoyat allaqachon ko'rib chiqilgan": "Эта жалоба уже рассмотрена",
    "Bu sizning challenge'ingiz emas": "Это не ваш челлендж",
    "Bu sizning isbotingiz emas": "Это не ваше доказательство",
    "Bu sizning rejangiz emas": "Это не ваш план",
    "Bu username band, boshqasini tanlang": "Это имя пользователя занято, выберите другое",
    "Bu vazifa bugun allaqachon tasdiqlangan": "Эта задача сегодня уже засчитана",
    "Bugun reja bo'yicha dam olish kuni": "Сегодня по плану день отдыха",
    "Bugungi rejada bunday vazifa yo'q": "В сегодняшнем плане нет такой задачи",
    "Bunday til yo'q": "Такого языка нет",
    "Challenge faol emas": "Челлендж не активен",
    "Challenge nomi bo'sh bo'lmasligi kerak": "Название челленджа не может быть пустым",
    "Challenge o'tgan sanadan boshlanishi mumkin emas": "Челлендж не может начаться в прошлом",
    "Challenge oxirgi kunida rejani o'zgartirib bo'lmaydi": "В последний день челленджа план менять нельзя",
    "Challenge topilmadi": "Челлендж не найден",
    "Faqat AI rad etgan isbot moderatorga yuboriladi": "Модератору отправляется только доказательство, отклонённое ИИ",
    "Faqat hali boshlanmagan challenge'ni bekor qilish mumkin": "Отменить можно только ещё не начавшийся челлендж",
    "Faqat ko'rib chiqilayotgan challenge rad etiladi": "Отклонить можно только челлендж на рассмотрении",
    "Faqat ko'rib chiqilayotgan challenge tasdiqlanadi": "Одобрить можно только челлендж на рассмотрении",
    "Faqat moderator isbotni tekshira oladi": "Проверять доказательства может только модератор",
    "Faqat rasm fayllari qabul qilinadi (JPG, PNG, HEIC emas)": "Принимаются только изображения (JPG, PNG; не HEIC)",
    "Foydalanish shartlari yangilangan. Iltimos, sahifani yangilang": "Условия использования обновились. Пожалуйста, обновите страницу",
    "Foydalanuvchi topilmadi": "Пользователь не найден",
    "Garov chegaralari noto'g'ri": "Неверные границы ставки",
    "Garovli challenge tugamaguncha akkauntni o'chirib bo'lmaydi": "Нельзя удалить аккаунт, пока не завершён челлендж со ставкой",
    "Garovli challenge'ingiz tugamagan. U yakunlangach akkauntni o'chira olasiz": "Ваш челлендж со ставкой ещё не завершён. Удалить аккаунт можно после него",
    "Google akkauntingizdagi email tasdiqlanmagan": "Почта в вашем Google-аккаунте не подтверждена",
    "Google bilan aloqa yo'q. Birozdan so'ng urinib ko'ring": "Нет связи с Google. Попробуйте чуть позже",
    "Google orqali kirish amalga oshmadi. Qayta urinib ko'ring": "Не удалось войти через Google. Попробуйте ещё раз",
    "Google orqali kirish yoqilmagan": "Вход через Google не включён",
    "Guruh topilmadi": "Группа не найдена",
    "Haftada kamida bir kun bo'sh vaqt ko'rsating": "Укажите свободное время хотя бы в один день недели",
    "Haftada kamida bitta ish kuni bo'lishi kerak": "В неделе должен быть хотя бы один рабочий день",
    "Hamyon hozircha yopiq — platforma bepul": "Кошелёк пока закрыт — платформа бесплатна",
    "Havola eskirgan. Saytdagi profilingizdan qaytadan ulang": "Ссылка устарела. Подключите заново из профиля на сайте",
    "Hisob topilmadi": "Счёт не найден",
    "Iltimos, tizimga kiring": "Пожалуйста, войдите в систему",
    "Isbot allaqachon tekshirilgan": "Доказательство уже проверено",
    "Isbot moderator ko'rigida emas": "Доказательство не на проверке у модератора",
    "Isbot topilmadi": "Доказательство не найдено",
    "Isbot uchun rasm yoki matn kerak": "Для доказательства нужно фото или текст",
    "Jadval 7 kundan iborat bo'lishi kerak": "Расписание должно состоять из 7 дней",
    "Kamida bitta isbot turi kerak": "Нужен хотя бы один тип доказательства",
    "Kod noto'g'ri yoki muddati o'tgan": "Код неверный или устарел",
    "Kunlik bo'sh vaqt 0 dan 16 soatgacha bo'lishi kerak": "Свободное время в день — от 0 до 16 часов",
    "Ledger muvozanatda emas": "Проводки не сбалансированы",
    "Mablag' yetarli emas": "Недостаточно средств",
    "Maqsadingizni yozing": "Напишите вашу цель",
    "Ma'lumot shu payt o'zgardi, qayta urinib ko'ring": "Данные только что изменились, попробуйте ещё раз",
    "Ma'lumot noto'g'ri": "Неверные данные",
    "Moderator topilmadi": "Модератор не найден",
    "Nol summali yozuv bo'lmaydi": "Запись с нулевой суммой невозможна",
    "O'z isbotingizni tekshira olmaysiz": "Нельзя проверять собственное доказательство",
    "O'zingiz haqingizda shikoyat qilib bo'lmaydi": "Нельзя пожаловаться на самого себя",
    "Oddiy rejimda garov bo'lmaydi": "В обычном режиме ставки нет",
    "Parolda harf ham, raqam ham bo'lsin": "В пароле должны быть и буквы, и цифры",
    "Pul qo'yish uchun avval telefon raqamingizni tasdiqlang": "Чтобы сделать ставку, сначала подтвердите номер телефона",
    "Pul qo'yish uchun challenge moderator tomonidan tasdiqlangan bo'lishi kerak": "Для ставки челлендж должен быть одобрен модератором",
    "Pulli rejim hozircha yopiq — barcha challenge'lar bepul 🎁": "Платный режим пока закрыт — все челленджи бесплатны 🎁",
    "Pulli rejimda reja challenge talabidan yengil bo'lishi mumkin emas": "В платном режиме план не может быть легче требований челленджа",
    "Pulli rejimda rejani faqat qiyinlashtirish mumkin": "В платном режиме план можно только усложнять",
    "Push obunasi kalitlari yo'q": "У push-подписки нет ключей",
    "Push obunasi noto'g'ri": "Неверная push-подписка",
    "Qiyinlik 1 dan 5 gacha bo'lishi kerak": "Сложность должна быть от 1 до 5",
    "Rad etish sababi yozilishi shart": "Нужно указать причину отказа",
    "Rasm 10 MB dan oshmasligi kerak": "Фото не должно превышать 10 МБ",
    "Reja topilmadi": "План не найден",
    "Ro'yxatdan o'tish uchun foydalanish shartlariga rozilik kerak": "Для регистрации нужно согласие с условиями использования",
    "Ruxsat yo'q": "Нет доступа",
    "Sessiya muddati tugagan, qayta kiring": "Сессия истекла, войдите снова",
    "Shikoyat topilmadi": "Жалоба не найдена",
    "Shikoyatingiz qabul qilingan va ko'rib chiqilmoqda": "Ваша жалоба принята и рассматривается",
    "Siz allaqachon shu guruhdasiz": "Вы уже в этой группе",
    "Siz bu challenge'da allaqachon qatnashyapsiz": "Вы уже участвуете в этом челлендже",
    "Summa butun son (so'm) bo'lishi kerak": "Сумма должна быть целым числом (сум)",
    "Summa manfiy bo'lishi mumkin emas": "Сумма не может быть отрицательной",
    "Summa noldan katta bo'lishi kerak": "Сумма должна быть больше нуля",
    "Taklif havolasi noto'g'ri yoki eskirgan": "Ссылка-приглашение неверна или устарела",
    "Taklif kodi noto'g'ri": "Неверный код приглашения",
    "Tasdiqlash uchun username'ingizni aynan yozing": "Для подтверждения введите своё имя пользователя точно",
    "Telefon raqami +998XXXXXXXXX formatida bo'lishi kerak": "Номер телефона должен быть в формате +998XXXXXXXXX",
    "Telegram bot hozircha ulanmagan": "Telegram-бот пока не подключён",
    "Telegram bot sozlanmagan": "Telegram-бот не настроен",
    "Topilmadi": "Не найдено",
    "Tranzaksiyada kamida ikki yozuv bo'ladi": "В транзакции должно быть минимум две записи",
    "Tugagan challenge rejasini o'zgartirib bo'lmaydi": "План завершённого челленджа менять нельзя",
    "Tugagan challenge'ga do'st taklif qilib bo'lmaydi": "В завершённый челлендж нельзя пригласить друзей",
    "Username 3-30 belgi: kichik lotin harflari, raqamlar va '_' bo'lishi kerak": "Имя пользователя: 3–30 символов — строчные латинские буквы, цифры и «_»",
    "Username yoki parol noto'g'ri": "Неверное имя пользователя или пароль",
    "Vaqt tugadi. Google orqali qaytadan kiring": "Время вышло. Войдите через Google ещё раз",
    "Vazifa nomi 1-120 belgi bo'lishi kerak": "Название задачи — от 1 до 120 символов",
}

# (Uzbek template, Russian template). "{}" marks a value; the Russian uses {0}, {1}... in order.
_TEMPLATES_RU: list[tuple[str, str]] = [
    (
        "Bir vaqtda ko'pi bilan {} ta pulli challenge",
        "Одновременно не больше {0} платных челленджей",
    ),
    ("Boshlanish sanasi {} kundan uzoq bo'lmasin", "Дата начала — не дальше чем через {0} дн."),
    (
        "Bu challenge '{}' turidagi isbotni qabul qilmaydi",
        "Этот челлендж не принимает доказательства типа «{0}»",
    ),
    (
        "Bu kun uchun isbot qabul qilinmaydi ({})",
        "За этот день доказательства не принимаются ({0})",
    ),
    ("Davomiylik {} kunlardan biri bo'lsin", "Длительность должна быть одной из: {0} дн."),
    ("Garov {} dan {} gacha bo'lishi kerak", "Ставка должна быть от {0} до {1}"),
    ("Guruh to'lgan ({} kishi)", "Группа заполнена ({0} человек)"),
    ("Har bir javob {} belgidan oshmasin", "Каждый ответ — не больше {0} символов"),
    (
        "Juda ko'p urinish. {} daqiqadan so'ng qayta urinib ko'ring",
        "Слишком много попыток. Попробуйте через {0} мин.",
    ),
    ("Matn {} belgidan oshmasin", "Текст — не больше {0} символов"),
    ("Ma'lumot noto'g'ri: {}", "Неверные данные: {0}"),
    ("Parol kamida {} belgi bo'lsin", "Пароль — минимум {0} символов"),
    ("Platformadan {} yoshdan foydalanish mumkin", "Пользоваться платформой можно с {0} лет"),
    (
        "Pulli rejim uchun reja haftada kamida {} kun va {} daqiqa majburiy ish bo'lishi kerak",
        "Для платного режима в плане нужно минимум {0} дн. и {1} мин. обязательной работы в неделю",
    ),
    ("Reja davomiyligi {} dan biri", "Длительность плана — одна из: {0}"),
    ("Vazifa kaliti noto'g'ri: {}", "Неверный ключ задачи: {0}"),
    ("Vazifa {} daqiqadan kam bo'lmasin", "Задача — не меньше {0} мин."),
    ("{} kuni allaqachon yopilgan ({})", "День {0} уже закрыт ({1})"),
    ("{} reja bo'yicha ish kuni emas", "{0} — не рабочий день по плану"),
    (
        "{}: bir kunga 12 soatdan ko'p reja qo'yilmaydi",
        "{0}: нельзя планировать больше 12 часов в день",
    ),
    ("{}: kamida bitta majburiy vazifa bo'lsin", "{0}: нужна хотя бы одна обязательная задача"),
    (
        "{}: reja {} daqiqa, bo'sh vaqtingizning 80% i esa {} daqiqa",
        "{0}: в плане {1} мин., а 80% вашего свободного времени — {2} мин.",
    ),
    ("{}: vazifa kalitlari takrorlanmasin", "{0}: ключи задач не должны повторяться"),
    ("{}: 1-{} belgi bo'lishi kerak", "{0}: от 1 до {1} символов"),
    ("Yo'l xaritasi 1-{} haftadan iborat bo'lsin", "Дорожная карта — от 1 до {0} недель"),
    ("1 dan {} tagacha maqsad kiriting", "Введите от 1 до {0} целей"),
    (
        "{}: tugash vaqti boshlanishidan keyin bo'lsin",
        "{0}: время окончания должно быть позже начала",
    ),
    ("{}: «{}» uchun vaqt belgilang", "{0}: укажите время для «{1}»"),
    ("{}: «{}» uyg'oq vaqtingizdan tashqarida", "{0}: «{1}» выходит за время бодрствования"),
    ("{}: «{}» va «{}» vaqti ustma-ust tushdi", "{0}: «{1}» и «{2}» пересекаются по времени"),
    ("Band vaqt nomi 1-{} belgi bo'lsin", "Название занятого времени — от 1 до {0} символов"),
    ("Band vaqtlar {} tadan oshmasin", "Занятых промежутков — не больше {0}"),
    ("{}: «{}» uchun bo'sh vaqt topilmadi", "{0}: для «{1}» не нашлось свободного времени"),
    ("Oylik marralar {} tadan oshmasin", "Месячных вех — не больше {0}"),
]

# Names that appear inside templated messages (weekdays, roadmap parts).
_NAMES_RU = {
    "Hafta mavzusi": "Тема недели",
    "Hafta maqsadi": "Цель недели",
    "Dars": "Урок",
    "Yakuniy natija": "Итоговый результат",
    "Oylik marra": "Месячная веха",
    "Dushanba": "Понедельник",
    "Seshanba": "Вторник",
    "Chorshanba": "Среда",
    "Payshanba": "Четверг",
    "Juma": "Пятница",
    "Shanba": "Суббота",
    "Yakshanba": "Воскресенье",
}


def _compile(template: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in template.split("{}")]
    return re.compile("^" + "(.+?)".join(parts) + "$", re.DOTALL)


_PATTERNS_RU = [(_compile(uz), ru) for uz, ru in _TEMPLATES_RU]


def _russian(message: str) -> str | None:
    if message in ERRORS_RU:
        return ERRORS_RU[message]
    for pattern, template in _PATTERNS_RU:
        match = pattern.match(message)
        if match:
            values = [_NAMES_RU.get(value, value) for value in match.groups()]
            return template.format(*values)
    return None


_TRANSLATORS: dict[str, Callable[[str], str | None]] = {"ru": _russian}


def translate_error(message: str, locale: str | None) -> str:
    translator = _TRANSLATORS.get((locale or "uz").split("-")[0].lower())
    return (translator(message) if translator else None) or message
