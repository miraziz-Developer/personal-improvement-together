# Yopiq beta — checklist

Maqsad: 20–50 ta tanish odam 2–3 hafta ishlatadi. Savol bitta: **odamlar qaytib kelishadimi?**

Belgilar: ✅ tekshirildi · ⚠️ e'tibor kerak · ⬜ qo'lda qilinadi

## 1. Kod va deploy (tekshirildi 2026-10-21)

- ✅ Backend: ruff, mypy, modul chegaralari (4/4), 254 test o'tdi (Postgres testlari CI'da)
- ✅ Frontend: tsc, eslint toza
- ✅ `main` CI va Deploy yashil
- ✅ Sayt (Vercel) va API `/health` 200 qaytaradi, javob ~0.7–0.9 s
- ✅ Sahifalar ochiladi: `/`, `/login`, `/register`, `/privacy`, `/terms`, `/tg`, manifest, service worker
- ✅ Telefonda (375px) gorizontal skroll yo'q, konsolda xato yo'q
- ✅ CORS faqat `pit-uz.vercel.app` ga ruxsat beradi, begona domenga yo'q
- ✅ HTTPS + HSTS (sayt ham, API ham)
- ✅ Urinish cheklovlari: ro'yxatdan o'tish, login, parol tiklash, SMS, isbot (40/soat), AI reja,
  guruh xabarlari, shikoyat
- ✅ Isbot rasmi 10 MB dan oshmaydi (sayt va bot)
- ✅ Shikoyat → moderator paneli (`/admin`) bor; ma'lumotni eksport/o'chirish bor
- ⚠️ API hujjati ochiq: `/docs`, `/openapi.json`. Beta uchun xavfli emas, ommaviy ochilishdan oldin yopish mumkin
- ⚠️ `robots.txt` yo'q (404). Beta uchun muhim emas

## 2. Server — o'zingiz tekshirasiz

Claude'ga production serverni o'qish ruxsat etilmagan. Buyruqlar faqat o'qiydi, sir qiymatlarni chiqarmaydi.
Avval `ssh pit-vm`, keyin serverning o'zida:

```bash
cd ~/pit; for k in PIT_ENV PIT_SENTRY_DSN PIT_AI_PROVIDERS BACKUP_CHAT_ID BACKUP_PASSPHRASE; do grep -qE "^$k=.+" deploy/.env.lite && echo "$k: bor" || echo "$k: YOQ"; done
```

- ⬜ `PIT_ENV` bor (production bo'lishi kerak: test to'lov tugmasi o'chadi)
- ⬜ `PIT_SENTRY_DSN` bor. Yo'q bo'lsa: sentry.io'da bepul loyiha oching, DSN'ni yozing, API'ni qayta ishga tushiring
- ⬜ `PIT_AI_PROVIDERS` bor. Yo'q bo'lsa isbotlar avtomatik tasdiqlanadi, rejalar shablondan tuziladi

```bash
docker logs --since 72h pit-lite-backup-1 2>&1 | tail -6
```

- ⬜ Har kuni `done` va `sent off-site` chiqyapti (`FAILED` yo'q)
- ⬜ Telegram chatda oxirgi kunlarning `.enc` fayllari bor

**Zaxirani haqiqatan tiklab ko'rish** — vaqtinchalik alohida konteynerda, ishlayotgan bazaga tegmaydi:

```bash
docker run --rm -v pit-lite_backups:/b:ro postgres:17-alpine sh -c 'f=$(ls -t /b/db-*.dump | head -1); echo "$f"; su postgres -c "initdb -D /tmp/pg >/dev/null && pg_ctl -D /tmp/pg -w start >/dev/null && createdb t && pg_restore -d t --no-owner --no-acl $f && psql -d t -tAc \"select count(*) from users\""'
```

- ⬜ Oxirgi kun fayli chiqdi va foydalanuvchilar soni ko'rindi (xatosiz)

```bash
docker logs --since 24h pit-lite-api-1 2>&1 | grep -ciE "traceback|error"; free -m | sed -n 2p
```

- ⬜ Xatolar soni 0 yoki tushunarli; bo'sh xotira (`available`) 200 MB dan ko'p

## 3. Kuzatuv (bepul)

- ⬜ UptimeRobot (yoki shunga o'xshash): `https://pit-uz.indiasouthcentral.cloudapp.azure.com/health` va
  `https://pit-uz.vercel.app`, har 5 daqiqada, ogohlantirish Telegram/email'ga
- ⬜ Sentry ogohlantirishlari emailga keladi

## 4. Azure — eng katta xavf

Obuna: Azure for Students, holati `Enabled`. Hozir 3 ta VM ishlayapti:

| VM | O'lcham | Kredit sarflaydimi |
|---|---|---|
| `pit-vm` | B1s | Yo'q (bepul daraja) |
| `bozorliii-vm` | B2ms | **Ha** |
| `tradingforex` | DS1_v2 | **Ha** |

Kredit tugasa butun obuna o'chadi — **PIT ham birga tushadi**. CLI kredit qoldig'ini ko'rsatmaydi.

- ⬜ https://www.microsoftazuresponsorships.com/Balance — qolgan kredit va tugash sanasi
- ⬜ Kerak bo'lmagan VM'ni to'xtatish (`Stop (deallocate)`), yoki kredit qachon tugashini bilib, oldindan reja qilish

## 5. Asosiy oqim — telefonda o'zingiz o'tib chiqing

Yangi akkaunt bilan, oddiy foydalanuvchidek:

- ⬜ Ro'yxatdan o'tish (sayt) va Telegram orqali kirish (Mini App)
- ⬜ Maqsad yozish → AI reja tuziladi
- ⬜ Kun tartibi (life plan) tuzish
- ⬜ Isbot yuborish: saytdan ham, botdan ham (`/bugun` → vazifa → rasm)
- ⬜ Ertasi kuni: ertalabki xabar keldi, streak o'sdi
- ⬜ Bir kun o'tkazib yuborish → freeze/streak to'g'ri ishladi
- ⬜ Do'stni taklif qilish havolasi, guruh ("together")
- ⬜ RU tilida ham bir marta o'tib chiqish
- ⬜ Parolni unutish → bot orqali tiklash

## 6. Beta odamlari uchun

- ⬜ Fikr-mulohaza kanali: Telegram guruh (xato + taklif)
- ⬜ Qisqa xabar: nima bu, nima qilish kerak, xatoni qayerga yozish
- ⬜ Har kuni 5 daqiqa: Sentry, guruh, `/admin` shikoyatlar

## 7. Nimani o'lchaymiz

- Ro'yxatdan o'tganlarning necha foizi birinchi isbotni yubordi
- 7-kun va 14-kun: hali ham isbot yuborayotganlar soni
- Eng ko'p tashlab ketilgan joy (qaysi qadamdan keyin qaytmadi)

Ommaviy ochilishdan oldin: frontend uchun asosiy oqim e2e testi, kattaroq server yoki zaxira reja, `/docs` ni yopish.
