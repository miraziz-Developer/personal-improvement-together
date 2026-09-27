import type { Metadata } from "next";

import { Localized } from "../Localized";

export const metadata: Metadata = { title: "Maxfiylik siyosati — PIT" };

export default function PrivacyPage() {
  return <Localized uz={<PrivacyUz />} ru={<PrivacyRu />} />;
}

function PrivacyUz() {
  return (
    <>
      <h1>Maxfiylik siyosati</h1>
      <p className="text-sm text-mist">Versiya: 2026-09-25</p>
      <p>Bu sahifa qaysi ma'lumotlaringizni yig'ishimiz, nima uchun va qanday himoya qilishimizni tushuntiradi.</p>

      <h2>1. Qanday ma'lumot yig'iladi</h2>
      <ul>
        <li>Username, tug'ilgan sana va hudud — yosh va hudud reytinglari uchun.</li>
        <li>Telefon raqam — faqat o'zingiz kiritsangiz; tasdiqlash va parolni tiklash uchun.</li>
        <li>Google orqali kirsangiz — Google hisobingiz identifikatori va email manzilingiz.</li>
        <li>Telegram botni ulasangiz — chat identifikatori, eslatma va xabarlar yuborish uchun.</li>
        <li>Brauzer bildirishnomalarini yoqsangiz — shu brauzerga xabar yuborish manzili.</li>
        <li>Maqsadlar, bo'sh vaqt va reja — shaxsiy reja tuzish uchun.</li>
        <li>Isbot rasmlari va matnlari — vazifa bajarilganini tekshirish uchun.</li>
        <li>Faollik: streak, ballar, bildirishnomalar.</li>
      </ul>

      <h2>2. Qanday himoya qilamiz</h2>
      <ul>
        <li>Parollar Argon2 bilan xeshlanadi — biz ham asl parolingizni ko'ra olmaymiz.</li>
        <li>Rasmlardagi metama'lumotlar (EXIF: joylashuv, qurilma) yuklashda o'chiriladi.</li>
        <li>Isbot rasmlari ochiq emas: ular 15 daqiqa amal qiladigan maxfiy havola orqaligina ko'rsatiladi.</li>
        <li>Barcha ulanishlar HTTPS orqali shifrlanadi.</li>
      </ul>

      <h2>3. Boshqalar nimani ko'radi</h2>
      <ul>
        <li>Reytingda faqat username, ball va streak ko'rinadi. Tug'ilgan sana, telefon va rasmlar ko'rinmaydi.</li>
        <li>10 kishidan kam bo'lgan yosh yoki hudud guruhlari reytingi yashiriladi — kichik guruhda shaxsni aniqlab bo'lmasligi uchun.</li>
        <li>Do'stlar guruhida a'zolar bir-birining username'i, streak'i va bugun bajargan-bajarmaganini ko'radi. Isbotlaringiz ularga ko'rinmaydi.</li>
      </ul>

      <h2>4. AI xizmatlari</h2>
      <p>
        Isbotlarni tekshirish va reja tuzish uchun rasm va matn AI xizmatiga (Google Gemini, Groq, OpenAI yoki Microsoft Azure OpenAI)
        yuborilishi mumkin. Unga username, telefon yoki tug'ilgan sanangiz yuborilmaydi.
      </p>

      <h2>5. Saqlash joyi va muddati</h2>
      <ul>
        <li>Shaxsiy ma'lumotlar O'zbekiston Respublikasi hududidagi serverlarda saqlanadi.</li>
        <li>Zaxira nusxalar 14 kun saqlanadi, keyin avtomatik o'chiriladi.</li>
        <li>
          Akkauntingizni Profil sahifasida istalgan vaqt o'zingiz o'chirasiz: shaxsiy ma'lumotlar, rasmlar va xabarlar darhol o'chiriladi,
          faqat anonim statistika (bajarilgan kunlar soni) qoladi.
        </li>
      </ul>

      <h2>6. Bolalar</h2>
      <p>
        18 yoshgacha bo'lgan foydalanuvchilar ota-ona yoki vasiy roziligi bilan ro'yxatdan o'tadi. Ota-ona farzandining ma'lumotlarini ko'rish
        yoki o'chirishni so'rashi mumkin.
      </p>

      <h2>7. Sizning huquqlaringiz</h2>
      <p>
        Profil sahifasida istalgan vaqt ma'lumotlaringiz nusxasini (JSON fayl) yuklab olasiz yoki akkauntni o'chirasiz. Tuzatish
        kerak bo'lsa — pastdagi manzilga yozing. Ma'lumotlaringizni sotmaymiz va reklama uchun uchinchi shaxslarga bermaymiz.
      </p>
    </>
  );
}

function PrivacyRu() {
  return (
    <>
      <h1>Политика конфиденциальности</h1>
      <p className="text-sm text-mist">Версия: 2026-09-25</p>
      <p>Здесь объясняется, какие данные мы собираем, зачем и как их защищаем.</p>

      <h2>1. Какие данные собираются</h2>
      <ul>
        <li>Имя пользователя, дата рождения и регион — для рейтингов по возрасту и региону.</li>
        <li>Номер телефона — только если вы его укажете; для подтверждения и восстановления пароля.</li>
        <li>При входе через Google — идентификатор вашего аккаунта Google и адрес электронной почты.</li>
        <li>Если подключите Telegram-бота — идентификатор чата, чтобы присылать напоминания и сообщения.</li>
        <li>Если включите уведомления в браузере — адрес для отправки уведомлений в этот браузер.</li>
        <li>Цели, свободное время и план — чтобы составить личный план.</li>
        <li>Фото и тексты доказательств — чтобы проверить выполнение задачи.</li>
        <li>Активность: серии, баллы, уведомления.</li>
      </ul>

      <h2>2. Как мы защищаем данные</h2>
      <ul>
        <li>Пароли хешируются Argon2 — даже мы не можем увидеть ваш исходный пароль.</li>
        <li>Метаданные фото (EXIF: местоположение, устройство) удаляются при загрузке.</li>
        <li>Фото доказательств не публичны: они открываются только по секретной ссылке, действующей 15 минут.</li>
        <li>Все соединения шифруются по HTTPS.</li>
      </ul>

      <h2>3. Что видят другие</h2>
      <ul>
        <li>В рейтинге видны только имя пользователя, баллы и серия. Дата рождения, телефон и фото не видны.</li>
        <li>Рейтинг возрастных и региональных групп меньше 10 человек скрывается — чтобы в маленькой группе нельзя было узнать человека.</li>
        <li>В группе друзей участники видят имена друг друга, серии и то, выполнил ли каждый задачу сегодня. Ваши доказательства им не видны.</li>
      </ul>

      <h2>4. Сервисы ИИ</h2>
      <p>
        Для проверки доказательств и составления плана фото и текст могут отправляться в сервис ИИ (Google Gemini, Groq, OpenAI или
        Microsoft Azure OpenAI). Имя пользователя, телефон и дата рождения туда не передаются.
      </p>

      <h2>5. Где и сколько хранятся данные</h2>
      <ul>
        <li>Персональные данные хранятся на серверах на территории Республики Узбекистан.</li>
        <li>Резервные копии хранятся 14 дней, затем удаляются автоматически.</li>
        <li>
          Вы можете в любой момент сами удалить аккаунт на странице «Профиль»: личные данные, фото и сообщения удаляются сразу, остаётся
          только анонимная статистика (число выполненных дней).
        </li>
      </ul>

      <h2>6. Дети</h2>
      <p>
        Пользователи младше 18 лет регистрируются с согласия родителя или опекуна. Родитель может попросить показать или удалить данные
        своего ребёнка.
      </p>

      <h2>7. Ваши права</h2>
      <p>
        На странице «Профиль» вы в любой момент можете скачать копию своих данных (файл JSON) или удалить аккаунт. Если что-то нужно
        исправить — напишите на адрес ниже. Мы не продаём ваши данные и не передаём их третьим лицам для рекламы.
      </p>
    </>
  );
}
