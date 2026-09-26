"""Everything the bot says, in every language it speaks. Keys, not sentences, live in the code."""

from typing import Final

LOCALES: Final = ("uz", "ru")

# Menu buttons: the bot recognises a tap by its text, in any language, because a user who
# switches language may still have the old keyboard on screen.
LABELS: Final[dict[str, dict[str, str]]] = {
    "uz": {
        "today": "📋 Bugungi vazifalar",
        "proof": "📸 Isbot yuborish",
        "status": "📊 Natijalarim",
        "settings": "⚙️ Sozlamalar",
        "later": "⏭ Keyinroq",
        "share_phone": "📱 Raqamni yuborish",
    },
    "ru": {
        "today": "📋 Задачи на сегодня",
        "proof": "📸 Отправить доказательство",
        "status": "📊 Мои результаты",
        "settings": "⚙️ Настройки",
        "later": "⏭ Позже",
        "share_phone": "📱 Отправить номер",
    },
}

TEXTS: Final[dict[str, dict[str, str]]] = {
    "uz": {
        "help": (
            "🤖 <b>Qanday ishlaydi</b>\n\n"
            "{today} — bugun nima qilish kerak\n"
            "{proof} — vazifani tanlang va rasm yuboring\n"
            "{status} — streak va progress\n"
            "{settings} — sayt va eslatmalar\n\n"
            "💡 Rasmni to'g'ridan-to'g'ri yuborsangiz ham bo'ladi — qaysi vazifa uchunligini "
            "o'zim so'rayman. Rasmga izoh yozsangiz, u ham isbotga qo'shiladi."
        ),
        "not_linked": (
            "👋 Assalomu alaykum! Men <b>PIT murabbiyi</b>man.\n\n"
            "Har kuni rejangizni eslatib turaman, isbotlaringizni qabul qilaman va har bir "
            "g'alabangizni nishonlayman 🔥\n\n"
            "Boshlash uchun saytda <b>Profil → Telegram'ni ulash</b> tugmasini bosing."
        ),
        "welcome": (
            "🎉 Salom, <b>{name}</b>! Telegram ulandi.\n\n"
            "Endi men sizga:\n"
            "☀️ ertalab — bugungi rejani,\n"
            "🌙 kechqurun — bajarilmagan vazifalarni,\n"
            "🏆 har bir yutuqda — tabrikni yuboraman.\n\n"
            "Hammasi pastdagi tugmalarda 👇"
        ),
        "checking": " · tekshirilmoqda",
        "in_review": " · moderator ko'rmoqda",
        "rejected": " · rad etildi, qayta yuboring",
        "later_ok": "Mayli! Keyinroq «{settings}» orqali tasdiqlaysiz 👌",
        "phone_already": "✅ Raqamingiz tasdiqlangan: {phone}",
        "already_linked": "Siz allaqachon ulangansiz ✅\n\n{help}",
        "cancelled": "👌 Bekor qilindi. Kerak bo'lsa, pastdagi menyudan tanlang.",
        "stop_ask": "🔕 Eslatmalar va tabriklar kelmay qoladi. Rostdan o'chiramizmi?",
        "stop_yes": "✅ Ha, o'chirish",
        "stop_no": "↩️ Yo'q",
        "stopped": (
            "👋 Eslatmalar to'xtatildi. Qaytmoqchi bo'lsangiz — saytda "
            "<b>Profil → Telegram'ni ulash</b>. Sizni kutib qolamiz!"
        ),
        "cheered": "👏 {name} olqishingizni oldi!",
        "cancel": "❌ Bekor qilish",
        "nothing_open": "🎉 Bugun isbot kutayotgan vazifa yo'q. Dam oling!",
        "which_task": "Qaysi vazifa uchun isbot yuborasiz? 👇",
        "ask_phone": (
            "📱 <b>Telefon raqamingizni tasdiqlaymiz</b>\n\n"
            "Pastdagi tugmani bosing — Telegram raqamingizni o'zi yuboradi, hech narsa "
            "yozish shart emas. Raqam parolni tiklash va akkaunt xavfsizligi uchun kerak."
        ),
        "own_number_only": "Faqat o'zingizning raqamingizni yuboring 👇",
        "phone_verified": "✅ Raqamingiz tasdiqlandi: <b>{phone}</b>",
        "settings_body": (
            "⚙️ <b>Sozlamalar</b>\n\n"
            "👤 Akkaunt: <b>{name}</b>\n"
            "{phone}\n"
            "☀️ Ertalabki reja — 08:00\n"
            "🌙 Kechki eslatma — 20:00 (bajarilmagan vazifa qolsa)"
        ),
        "phone_ok": "📱 Telefon: {phone} ✅",
        "phone_missing": "📱 Telefon: tasdiqlanmagan",
        "btn_verify_phone": "📱 Telefonni tasdiqlash",
        "btn_site": "🌐 Saytda ochish",
        "btn_help": "❓ Yordam",
        "btn_stop": "🔕 Eslatmalarni o'chirish",
        "no_photo_tasks": "Bugun rasm kutayotgan vazifa yo'q 🙂 Ro'yxat: {today}",
        "photo_which": "📸 Rasm keldi! Qaysi vazifa uchun?",
        "press_proof": "Isbot yuborish uchun pastdagi «{proof}» tugmasini bosing 👇",
        "needs_photo": "Bu vazifa uchun rasm kerak 📸 Rasmni yuboring.",
        "accepted": (
            "📨 <b>{title}</b> — isbot qabul qilindi!\nTekshirib, natijani shu yerga yozaman ⏳"
        ),
        "no_active": "Hozir faol challenge yo'q. Yangisini boshlash vaqti keldi! 🚀",
        "btn_pick_challenge": "🚀 Challenge tanlash",
        "pick_footer": "Isbot yuborish uchun vazifani tanlang 👇",
        "all_done": "Bugungi hammasi joyida 🎉 Ertaga yana davom etamiz!",
        "today_header": "📋 <b>Bugun</b> — {date}",
        "status_title": "📊 <b>Natijalaringiz</b>",
        "status_block": (
            "<b>{title}</b>\n"
            "🔥 Streak: {streak} kun (rekord: {best})\n"
            "📅 Bajarildi: {done} / {total} kun\n"
            "🧊 Freeze: {freezes} ta"
        ),
        "no_active_status": "Faol challenge yo'q. Saytda yangisini boshlang 🚀",
        "starts_on": "⏳ {date} kuni boshlanadi",
        "rest_day": "😌 Bugun dam olish kuni — kuch yig'ing!",
        "optional": " · ixtiyoriy",
        "task_line": "{icon} {title} — {minutes} daq{optional}{note}",
        "daily_code": "🔑 Kunlik kod: <code>{code}</code> (rasmda ko'rinsin)",
        "not_found": "Challenge topilmadi",
        "not_in_plan": "Bu vazifa bugungi rejada yo'q. Ro'yxat: {today}",
        "ask_photo_or_text": (
            "📸 <b>{title}</b> uchun rasm yuboring yoki nima qilganingizni yozing."
        ),
        "ask_photo": "📸 <b>{title}</b> uchun rasm yuboring.",
        "ask_text": "✍️ <b>{title}</b> uchun nima qilganingizni yozib yuboring.",
        "code_in_photo": "\n🔑 Rasmda bugungi kod ko'rinsin: <code>{code}</code>",
        "btn_send_proof": "📸 Isbot yuborish",
        "btn_today": "📋 Bugungi vazifalar",
        "btn_cheer": "👏 Olqishlash",
        "task_approved": "✅ <b>{title}</b> tasdiqlandi!",
        "remaining": "\nYana {n} ta majburiy vazifa qoldi — davom eting 💪",
        "bonus": "\nQo'shimcha ball qo'shildi ⭐",
    },
    "ru": {
        "help": (
            "🤖 <b>Как это работает</b>\n\n"
            "{today} — что сделать сегодня\n"
            "{proof} — выберите задачу и отправьте фото\n"
            "{status} — серия и прогресс\n"
            "{settings} — сайт и напоминания\n\n"
            "💡 Можно сразу прислать фото — я сам спрошу, к какой задаче оно относится. "
            "Подпись к фото тоже добавится к доказательству."
        ),
        "not_linked": (
            "👋 Здравствуйте! Я <b>коуч PIT</b>.\n\n"
            "Каждый день напоминаю о плане, принимаю доказательства и отмечаю каждую "
            "вашу победу 🔥\n\n"
            "Чтобы начать, на сайте нажмите <b>Профиль → Подключить Telegram</b>."
        ),
        "welcome": (
            "🎉 Привет, <b>{name}</b>! Telegram подключён.\n\n"
            "Теперь я буду присылать:\n"
            "☀️ утром — план на день,\n"
            "🌙 вечером — невыполненные задачи,\n"
            "🏆 после каждой победы — поздравление.\n\n"
            "Всё — в кнопках внизу 👇"
        ),
        "checking": " · проверяется",
        "in_review": " · смотрит модератор",
        "rejected": " · отклонено, отправьте снова",
        "later_ok": "Хорошо! Подтвердить можно позже через «{settings}» 👌",
        "phone_already": "✅ Ваш номер подтверждён: {phone}",
        "already_linked": "Вы уже подключены ✅\n\n{help}",
        "cancelled": "👌 Отменено. Если нужно — выберите в меню внизу.",
        "stop_ask": "🔕 Напоминания и поздравления перестанут приходить. Точно отключить?",
        "stop_yes": "✅ Да, отключить",
        "stop_no": "↩️ Нет",
        "stopped": (
            "👋 Напоминания отключены. Захотите вернуться — на сайте "
            "<b>Профиль → Подключить Telegram</b>. Будем ждать!"
        ),
        "cheered": "👏 {name} получил(а) ваши аплодисменты!",
        "cancel": "❌ Отмена",
        "nothing_open": "🎉 Сегодня нет задач, ждущих доказательства. Отдыхайте!",
        "which_task": "Для какой задачи отправляете доказательство? 👇",
        "ask_phone": (
            "📱 <b>Подтвердим номер телефона</b>\n\n"
            "Нажмите кнопку внизу — Telegram сам отправит ваш номер, ничего вводить не нужно. "
            "Номер нужен для восстановления пароля и безопасности аккаунта."
        ),
        "own_number_only": "Отправьте, пожалуйста, свой собственный номер 👇",
        "phone_verified": "✅ Номер подтверждён: <b>{phone}</b>",
        "settings_body": (
            "⚙️ <b>Настройки</b>\n\n"
            "👤 Аккаунт: <b>{name}</b>\n"
            "{phone}\n"
            "☀️ Утренний план — 08:00\n"
            "🌙 Вечернее напоминание — 20:00 (если остались задачи)"
        ),
        "phone_ok": "📱 Телефон: {phone} ✅",
        "phone_missing": "📱 Телефон: не подтверждён",
        "btn_verify_phone": "📱 Подтвердить телефон",
        "btn_site": "🌐 Открыть сайт",
        "btn_help": "❓ Помощь",
        "btn_stop": "🔕 Отключить напоминания",
        "no_photo_tasks": "Сегодня нет задач, ждущих фото 🙂 Список: {today}",
        "photo_which": "📸 Фото получено! Для какой задачи?",
        "press_proof": "Чтобы отправить доказательство, нажмите «{proof}» внизу 👇",
        "needs_photo": "Для этой задачи нужно фото 📸 Отправьте фото.",
        "accepted": (
            "📨 <b>{title}</b> — доказательство принято!\nПроверю и напишу результат сюда ⏳"
        ),
        "no_active": "Сейчас нет активных челленджей. Самое время начать новый! 🚀",
        "btn_pick_challenge": "🚀 Выбрать челлендж",
        "pick_footer": "Выберите задачу, чтобы отправить доказательство 👇",
        "all_done": "На сегодня всё сделано 🎉 Завтра продолжим!",
        "today_header": "📋 <b>Сегодня</b> — {date}",
        "status_title": "📊 <b>Ваши результаты</b>",
        "status_block": (
            "<b>{title}</b>\n"
            "🔥 Серия: {streak} дн. (рекорд: {best})\n"
            "📅 Выполнено: {done} / {total} дн.\n"
            "🧊 Заморозки: {freezes}"
        ),
        "no_active_status": "Активных челленджей нет. Начните новый на сайте 🚀",
        "starts_on": "⏳ Начнётся {date}",
        "rest_day": "😌 Сегодня день отдыха — набирайтесь сил!",
        "optional": " · необязательно",
        "task_line": "{icon} {title} — {minutes} мин{optional}{note}",
        "daily_code": "🔑 Код дня: <code>{code}</code> (должен быть виден на фото)",
        "not_found": "Челлендж не найден",
        "not_in_plan": "Этой задачи нет в сегодняшнем плане. Список: {today}",
        "ask_photo_or_text": "📸 Для «{title}» отправьте фото или напишите, что вы сделали.",
        "ask_photo": "📸 Для «{title}» отправьте фото.",
        "ask_text": "✍️ Для «{title}» напишите, что вы сделали.",
        "code_in_photo": "\n🔑 На фото должен быть виден код дня: <code>{code}</code>",
        "btn_send_proof": "📸 Отправить доказательство",
        "btn_today": "📋 Задачи на сегодня",
        "btn_cheer": "👏 Поаплодировать",
        "task_approved": "✅ <b>{title}</b> засчитано!",
        "remaining": "\nОсталось обязательных задач: {n} — продолжайте 💪",
        "bonus": "\nДобавлены бонусные баллы ⭐",
    },
}

MONTHS: Final = {
    "uz": ("yanvar", "fevral", "mart", "aprel", "may", "iyun",
           "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"),
    "ru": ("января", "февраля", "марта", "апреля", "мая", "июня",
           "июля", "августа", "сентября", "октября", "ноября", "декабря"),
}  # fmt: skip
WEEKDAYS: Final = {
    "uz": ("dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"),
    "ru": ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"),
}


def pick(locale: str | None) -> str:
    """The user's language if the bot speaks it, else Uzbek. Accepts codes like 'ru-RU'."""
    code = (locale or "uz").split("-")[0].lower()
    return code if code in LOCALES else "uz"


def tr(locale: str, key: str, **values: object) -> str:
    text = TEXTS[pick(locale)].get(key, TEXTS["uz"][key])
    return text.format(**values) if values else text


def label(locale: str, key: str) -> str:
    return LABELS[pick(locale)][key]


def label_action(text: str) -> str | None:
    """Which menu button this text is, in whichever language it was shown."""
    for labels in LABELS.values():
        for action, shown in labels.items():
            if shown == text:
                return action
    return None
