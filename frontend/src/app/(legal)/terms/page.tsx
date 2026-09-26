import type { Metadata } from "next";

export const metadata: Metadata = { title: "Foydalanish shartlari — PIT" };

export default function TermsPage() {
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
        Shartlar yangilanganda versiya sanasi o'zgaradi va sizdan qaytadan rozilik so'ralishi mumkin. Akkauntingizni o'chirishni istasangiz,
        pastdagi manzilga yozing.
      </p>
    </>
  );
}
