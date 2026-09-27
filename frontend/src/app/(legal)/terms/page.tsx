import type { Metadata } from "next";

import { Localized } from "../Localized";

export const metadata: Metadata = { title: "Foydalanish shartlari — PIT" };

export default function TermsPage() {
  return <Localized uz={<TermsUz />} ru={<TermsRu />} />;
}

function TermsUz() {
  return (
    <>
      <h1>Foydalanish shartlari</h1>
      <p className="text-sm text-mist">Versiya: 2026-09-25</p>
      <p>
        PIT (Personal Improvement Together) — maqsadlarni kundalik odatga aylantirishga yordam beruvchi platforma. Ro'yxatdan o'tib, siz
        quyidagi shartlarga rozilik bildirasiz.
      </p>

      <h2>1. Kim foydalana oladi</h2>
      <ul>
        <li>Platformadan 7 yoshdan boshlab foydalanish mumkin.</li>
        <li>18 yoshga to'lmagan foydalanuvchilar ota-onasi yoki vasiysining roziligi bilan ro'yxatdan o'tadi.</li>
        <li>Bir kishi — bitta akkaunt. Parolingizni boshqalarga bermang.</li>
      </ul>

      <h2>2. Challenge va isbotlar</h2>
      <ul>
        <li>Rejadagi barcha majburiy vazifalar isbot bilan tasdiqlansa, kun bajarilgan hisoblanadi.</li>
        <li>Faqat o'zingiz olgan va o'z harakatingizni ko'rsatuvchi rasm yoki matn yuboring.</li>
        <li>Isbotlarni AI tekshiradi; shubhali holatlarni moderator ko'rib chiqadi.</li>
        <li>Birovning rasmi, soxta isbot yoki bir rasmni qayta yuborish akkauntni cheklashga olib kelishi mumkin.</li>
      </ul>

      <h2>3. Pulli rejim (garov)</h2>
      <p>
        Hozircha pulli funksiyalar o'chirilgan — platforma to'liq bepul. Garov rejimi ishga tushirilganda uning alohida shartlari e'lon
        qilinadi va siz ulardan oldindan xabardor bo'lasiz.
      </p>

      <h2>4. Xulq-atvor qoidalari</h2>
      <ul>
        <li>Username va isbotlarda haqoratli, zo'ravonlik yoki kattalarga oid kontent taqiqlanadi.</li>
        <li>Platformani buzishga yoki avtomatik so'rovlar bilan ortiqcha yuklashga urinish taqiqlanadi.</li>
        <li>Nomaqbul kontent yoki username ko'rsangiz, yonidagi bayroqcha belgisi orqali shikoyat qiling — moderator ko'rib chiqadi.</li>
        <li>Qoidabuzarlikda akkaunt vaqtincha yoki butunlay bloklanishi mumkin.</li>
      </ul>

      <h2>5. Sog'liq haqida</h2>
      <p>
        Murabbiy xabarlari va AI rejalar umumiy motivatsiya uchun, tibbiy maslahat emas. Jismoniy mashqlar yoki ovqatlanishni
        o'zgartirishdan oldin, ayniqsa sog'lig'ingizda muammo bo'lsa, shifokor bilan maslahatlashing.
      </p>

      <h2>6. Javobgarlik</h2>
      <p>Platformani barqaror ishlatishga harakat qilamiz, ammo texnik uzilishlar bo'lishi mumkin.</p>

      <h2>7. O'zgarishlar va akkauntni o'chirish</h2>
      <p>
        Shartlar yangilanganda versiya sanasi o'zgaradi va sizdan qaytadan rozilik so'ralishi mumkin. Akkauntingizni istalgan vaqt
        Profil sahifasida o'zingiz o'chirasiz.
      </p>
    </>
  );
}

function TermsRu() {
  return (
    <>
      <h1>Условия использования</h1>
      <p className="text-sm text-mist">Версия: 2026-09-25</p>
      <p>
        PIT (Personal Improvement Together) — платформа, которая помогает превращать цели в ежедневные привычки. Регистрируясь, вы
        соглашаетесь с условиями ниже.
      </p>

      <h2>1. Кто может пользоваться</h2>
      <ul>
        <li>Пользоваться платформой можно с 7 лет.</li>
        <li>Пользователи младше 18 лет регистрируются с согласия родителя или опекуна.</li>
        <li>Один человек — один аккаунт. Не передавайте свой пароль другим.</li>
      </ul>

      <h2>2. Челленджи и доказательства</h2>
      <ul>
        <li>День засчитывается, когда все обязательные задачи плана подтверждены доказательством.</li>
        <li>Отправляйте только фото или текст, которые сделали вы сами и которые показывают ваше действие.</li>
        <li>Доказательства проверяет ИИ; спорные случаи рассматривает модератор.</li>
        <li>Чужое фото, поддельное доказательство или повторная отправка одного фото могут привести к ограничению аккаунта.</li>
      </ul>

      <h2>3. Платный режим (ставка)</h2>
      <p>
        Сейчас платные функции отключены — платформа полностью бесплатна. Когда режим ставок заработает, его отдельные условия будут
        опубликованы заранее, и вы узнаете о них до начала.
      </p>

      <h2>4. Правила поведения</h2>
      <ul>
        <li>В имени пользователя и доказательствах запрещены оскорбления, насилие и контент для взрослых.</li>
        <li>Запрещено пытаться взломать платформу или перегружать её автоматическими запросами.</li>
        <li>Увидели недопустимый контент или имя — пожалуйтесь через значок флажка рядом с ним, модератор всё проверит.</li>
        <li>За нарушения аккаунт может быть заблокирован временно или навсегда.</li>
      </ul>

      <h2>5. О здоровье</h2>
      <p>
        Сообщения коуча и планы ИИ — это общая мотивация, а не медицинский совет. Прежде чем менять физическую нагрузку или питание,
        особенно при проблемах со здоровьем, посоветуйтесь с врачом.
      </p>

      <h2>6. Ответственность</h2>
      <p>Мы стараемся, чтобы платформа работала стабильно, но технические перебои возможны.</p>

      <h2>7. Изменения и удаление аккаунта</h2>
      <p>
        При обновлении условий меняется дата версии, и мы можем снова попросить ваше согласие. Удалить аккаунт можно в любой момент
        самостоятельно на странице «Профиль».
      </p>
    </>
  );
}
