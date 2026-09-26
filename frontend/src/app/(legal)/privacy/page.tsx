import type { Metadata } from "next";

export const metadata: Metadata = { title: "Maxfiylik siyosati — PIT" };

export default function PrivacyPage() {
  return (
    <>
      <h1>Maxfiylik siyosati</h1>
      <p className="text-sm text-mist">Versiya: 2026-09-25</p>
      <p>Bu sahifa qaysi ma'lumotlaringizni yig'ishimiz, nima uchun va qanday himoya qilishimizni tushuntiradi.</p>

      <h2>1. Qanday ma'lumot yig'iladi</h2>
      <ul>
        <li>Username, tug'ilgan sana va hudud — yosh va hudud reytinglari uchun.</li>
        <li>Telefon raqam — faqat o'zingiz kiritsangiz; tasdiqlash va parolni tiklash SMS'lari uchun.</li>
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
      </ul>

      <h2>4. AI xizmatlari</h2>
      <p>
        Isbotlarni tekshirish va reja tuzish uchun rasm va matn AI xizmatiga (OpenAI, Google Gemini yoki Microsoft Azure OpenAI) yuborilishi mumkin. Unga
        username, telefon yoki tug'ilgan sanangiz yuborilmaydi.
      </p>

      <h2>5. Saqlash joyi va muddati</h2>
      <ul>
        <li>Shaxsiy ma'lumotlar O'zbekiston Respublikasi hududidagi serverlarda saqlanadi.</li>
        <li>Zaxira nusxalar 14 kun saqlanadi, keyin avtomatik o'chiriladi.</li>
        <li>So'rovingiz bo'yicha akkauntingiz, shaxsiy ma'lumotlaringiz va rasmlaringiz o'chiriladi.</li>
      </ul>

      <h2>6. Bolalar</h2>
      <p>
        18 yoshgacha bo'lgan foydalanuvchilar ota-ona yoki vasiy roziligi bilan ro'yxatdan o'tadi. Ota-ona farzandining ma'lumotlarini ko'rish
        yoki o'chirishni so'rashi mumkin.
      </p>

      <h2>7. Sizning huquqlaringiz</h2>
      <p>
        Ma'lumotlaringiz nusxasini olish, tuzatish yoki o'chirishni so'rashingiz mumkin — pastdagi manzilga yozing. Ma'lumotlaringizni
        sotmaymiz va reklama uchun uchinchi shaxslarga bermaymiz.
      </p>
    </>
  );
}
