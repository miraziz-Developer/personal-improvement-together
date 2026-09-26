# PRD — Personal Improvement Together

> Versiya: 0.4 · Sana: 2026-09-24 · Holat: qoralama (ochiq qarorlar oxirida)
>
> **Qabul qilingan qarorlar:** (1) challenge bajarilmasa, garov platformada qoladi, shuning uchun tekshiruv adolatli bo'lishi shart (§6.3). (2) Backend: FastAPI + DDD modular monolit (§11).

## 1. Maqsad

Odamlarga maqsadlariga erishishda yordam beradigan platforma. Uch asosiy mexanizm bor:

1. **Isbot (Proof-of-Work).** Har kuni bajarilgan ish isbotlanadi, AI tekshiradi.
2. **Raqobat.** Tengdoshlar (tug'ilgan yil), hudud va do'stlar bilan reyting.
3. **Majburiyat (Commitment).** Ixtiyoriy ravishda pul muzlatiladi va challenge muvaffaqiyatli tugasa to'liq qaytariladi.

**Asosiy tamoyil:** platforma foydalanuvchining **muvaffaqiyatidan** manfaatdor bo'lishi kerak, muvaffaqiyatsizligidan emas.

---

## 2. Challenge rejimlari

Har bir challenge'ga ikki rejimda qo'shilish mumkin. Rejimni foydalanuvchi tanlaydi.

| | **Oddiy rejim** | **Majburiyat rejimi (Stake)** |
|---|---|---|
| Pul | Yo'q | Foydalanuvchi summa muzlatadi (masalan 100 000 so'm) |
| Kim uchun | Hamma (7 yoshdan) | Hamma yosh; telefon raqami tasdiqlangan bo'lishi kerak (bola uchun ota-ona raqami ham bo'ladi). Bolalar uchun pulni ota-ona to'laydi |
| Muvaffaqiyat | Ball, badge, reyting | Pul **100% qaytariladi** + ball, badge, reyting |
| Muvaffaqiyatsizlik | Streak uziladi | Muzlatilgan pul **platformada qoladi** |
| AI rad etsa | Qayta yuborish mumkin | Qayta yuborish mumkin. Pul **hech qachon faqat AI qarori bilan kuymaydi**, oxirgi so'zni moderator aytadi (§6.3) |

**Muhim:** muvaffaqiyatli foydalanuvchiga yutqazganlar pulidan **hech qanday pul bonus berilmaydi**. Aynan shu narsa tizimni tikish yoki qimordan ajratib turadi. Mukofotlar faqat ball, badge, reyting va homiylar sovg'alari ko'rinishida bo'ladi.

## 2.1. Foydalanuvchi yo'li

```
1. Register            username, tug'ilgan sana (7+), hudud, telefon
2. Ikki yo'l:
   A) "Menga reja tuz"  → onboarding savollari: maqsad, nega, hozirgi daraja, xalaqit beradigan
                          narsa, har kuni necha daqiqa bo'sh vaqt bor
                        → AI reja tuzadi: haftalik jadval + har kunning vazifalari
                          (bo'sh vaqtning ko'pi bilan 80% i; oshsa, reja rad etiladi)
                        → foydalanuvchi rejani ko'radi, tahrirlaydi
   B) "Tayyor challenge" → katalogdan tanlaydi (onboarding majburiy emas)
3. Boshlash            oddiy yoki pulli rejim (garov muzlatiladi)
4. Har kuni            bugungi vazifalar → har biriga isbot → AI → moderator (kerak bo'lsa)
5. Yakun               garov qaytadi, ball, reyting
```

**Tushunchalar:** Challenge (maqsad bosqichi, garov shu darajada) → Jadval (hafta kunlari) → Vazifa (task, isbot shu darajada).

**Qoidalar (✅ qabul qilingan):**
- **Kun bajarilgan** hisoblanadi, qachonki o'sha kunning **barcha majburiy vazifalari** tasdiqlansa. Qo'shimcha vazifalar faqat ball beradi (har 10 daqiqaga 1 ball, ko'pi bilan 5; eng arzon majburiy kun 10 ball).
- **Dam olish kunlari** (jadvalda vazifa yo'q kunlar) hech qachon "o'tkazib yuborilgan" hisoblanmaydi.
- **Rejani o'zgartirish** ertangi kundan kuchga kiradi, o'tgan kunlar eski reja bo'yicha qoladi. Pulli rejimda faqat **qiyinlashtirish** mumkin (ish kunlari soni va haftalik majburiy daqiqalar kamaymasligi kerak).
- **Pulli rejim minimumi:** haftada kamida 3 ish kuni va 90 daqiqa majburiy ish. Aks holda "haftada 5 daqiqa" rejaga pul qo'yib, uni oson qaytarib olish mumkin bo'lardi.
- AI tuzgan reja moderatsiyasiz challenge bo'ladi (mezonni AI yozgan). Foydalanuvchi o'zi yozgan challenge'ga pul qo'yish uchun esa moderator tasdig'i kerak.

---

## 3. Challenge turlari

### 3.1. Shablon challenge'lar (admin yaratadi)
Masalan: "30 kun kod yozish", "21 kun sport zali", "30 kun har kuni 20 bet kitob".
Har bir shablonda:
- `category`: sport | code | study | reading | health | custom
- `duration_days`: 7 / 14 / 21 / 30 / 60 / 90
- `proof_types`: qaysi isbotlar qabul qilinadi (photo, text, github, strava)
- `verification_prompt`: AI uchun aniq mezon (masalan: "rasmda sport zali jihozlari va foydalanuvchi ko'rinishi kerak")
- `difficulty`: 1–5 (ball koeffitsienti)
- `stake_allowed`, `min_stake`, `max_stake`

### 3.2. Shaxsiy challenge'lar (foydalanuvchi yaratadi)
Foydalanuvchi o'z maqsadi va mezonini yozadi. **Stake rejimida faqat moderator tasdiqlagandan keyin** ishga tushadi, aks holda odam o'ziga juda oson mezon yozib olishi mumkin.

### 3.3. Guruh challenge'lari ("Together")
- Do'stlar bitta challenge'ni **bir kunda** boshlaydi (umumiy `start_date`).
- Guruh ichida alohida reyting va lenta bo'ladi (kim bugun isbot yubordi, kim yubormadi).
- **Jamoa streak'i:** hamma bajarsa, jamoa bonus ball oladi.
- Stake har kim uchun alohida. Guruh a'zolari bir-birining puliga ta'sir qilmaydi.

---

## 4. Kunlik sikl va challenge hayot sikli

### 4.1. Participation (foydalanuvchining challenge'dagi ishtiroki) holatlari

```
join ──▶ scheduled ──(start_date)──▶ active ──▶ completed  (hamma kun done/frozen → garov qaytadi)
            │                           └─────▶ failed     (kun missed, freeze qolmagan → garov platformaga)
            └──(boshlanmasdan bekor)──▶ cancelled (garov 100% qaytadi)
```

- Garov join paytida **o'sha tranzaksiyaning o'zida** muzlatiladi. Hisobda pul yetmasa, ishtirok umuman yaratilmaydi, shuning uchun `pending_payment` holati kerak emas. Pul oldin hamyonga tushiriladi (deposit).
- Challenge **boshlanganidan keyin** bekor qilib bo'lmaydi (aks holda qiyin kuni pulni olib chiqib ketish mumkin bo'lardi).

**Kun holatlari:** `pending` → `done` | `frozen` | `missed` | `awaiting_review` (natija moderator yoki kechikkan AI javobini kutmoqda).

### 4.2. Kunlik muddat
- Kun foydalanuvchining vaqt zonasi bo'yicha 00:00–23:59 ga teng. Standart vaqt zonasi `Asia/Tashkent`.
- Hisob **`submitted_at` bo'yicha** yuritiladi. 23:58 da yuborilgan isbotni AI 00:10 da tasdiqlasa ham, u o'sha kunga hisoblanadi.
- AI rad etgan bo'lsa, foydalanuvchi **o'sha kun tugaguncha qayta yuborishi mumkin**. Bitta rad etilgan urinish challenge'ni buzmaydi.

### 4.3. Freeze (dam olish kuni)
- Har **10 ish kuni uchun 1 ta freeze** beriladi (dam olish kunlari hisobga kirmaydi). Kasallik va favqulodda holatlar uchun.
- Kun o'tkazib yuborilsa va freeze qolgan bo'lsa, u **avtomatik** ishlatiladi.
- Freeze kunlari ball bermaydi, lekin streak'ni ham uzmaydi.

### 4.4. Kunlik tekshiruv jobi (Celery Beat, har kuni 00:15)
Har bir ochiq Participation uchun tugagan har bir kun tekshiriladi (`CloseDays` buyrug'i):
1. `approved` isbot bor → kun `done`.
2. `pending` yoki `needs_review` isbot bor → kun `awaiting_review`, yakuniy qaror chiqqach qayta hisoblanadi.
3. **Stake rejimi:** faqat AI rad etgan isbot bor → kun `awaiting_review`, eng oxirgi isbot avtomatik moderatorga yuboriladi.
4. Isbot yo'q yoki rad etishni **moderator tasdiqlagan** (stake), yoxud oddiy rejimda AI rad etgan → freeze bor bo'lsa ishlatiladi, bo'lmasa `failed`.
5. Barcha kunlar `done` yoki `frozen` → `completed` va pul qaytariladi.

Job **idempotent** bo'lishi shart: ikki marta ishlasa ham natija bir xil bo'ladi.

---

## 5. Pul tizimi (Wallet)

### 5.1. Oqim
```
Karta ──(Payme/Click)──▶ Wallet.available ──(join)──▶ Wallet.locked
                                                         │
                          ┌──────────────────────────────┴───────────────┐
                          ▼ completed / cancelled                        ▼ failed
                   Wallet.available                              Forfeit (§5.4)
                          │
                          ▼ (withdraw)
                        Karta
```

**Nima uchun karta "hold"i emas, wallet?** Bank kartasidagi hold (pre-authorization) odatda bir necha kundan keyin avtomatik bekor bo'ladi, challenge'lar esa 30–90 kun davom etadi. Shuning uchun pul platformaning hisobiga o'tkaziladi va ichki balansda "muzlatilgan" deb belgilanadi.

### 5.2. Qoidalar
- Summalar **butun son (so'm)** sifatida saqlanadi, `BIGINT`. Float ishlatilmaydi.
- **Double-entry ledger:** har bir operatsiya ikki yozuvdan iborat (bir hisobdan chiqim, boshqasiga kirim). Hisoblar: `user_available`, `user_locked` (muzlatilgan garov), `platform_revenue`, `external` (to'lov provayderlari). Yozuvlar yig'indisi har doim 0.
- Balans faqat DB tranzaksiyasi ichida o'zgaradi (`SELECT ... FOR UPDATE`).
- Har bir pul operatsiyasida `idempotency_key` bor. Ikki marta bosilganda pul ikki marta yechilmaydi.
- To'lov provayderining webhook'lari imzo bilan tekshiriladi va idempotent qayta ishlanadi.
- Cheklovlar (v1): min 10 000 so'm, max 2 000 000 so'm. Bir vaqtda ko'pi bilan 3 ta stake challenge.

### 5.3. Daromad modeli
- **Bajarilmagan challenge'lar garovi** (`stake_forfeit` → `platform_revenue` hisobi).
- Premium obuna: statistika, cheksiz shaxsiy challenge'lar, guruhlar.
- Homiylik challenge'lari: brend sovg'a beradi.

### 5.4. Muvaffaqiyatsizlikda pul — ✅ QAROR: platformada qoladi
Bu yerda manfaatlar to'qnashuvi bor: AI isbotni rad etsa, platforma pul ishlaydi. Shuning uchun ishonchni tizim darajasida kafolatlaymiz (§6.3):
- pul **hech qachon faqat AI qarori bilan** kuymaydi;
- har bir rad etishning **sababi** foydalanuvchiga ko'rsatiladi;
- har bir pul harakati ledger va audit log'da yoziladi.

---

## 6. Isbotni tekshirish (AI Proof pipeline)

### 6.1. Oqim
1. Frontend backend'dan **presigned upload URL** oladi va faylni to'g'ridan-to'g'ri Blob/S3 ga yuklaydi.
2. `POST /proofs` so'roviga `file_key`, `text_note` va `phash` yuboriladi. `for_date` va kutilgan kunlik kodni server o'zi hisoblaydi (mijozga ishonilmaydi). Proof `pending` bo'lib saqlanadi va Celery task navbatga qo'yiladi.
3. Worker quyidagi bosqichlarni bajaradi:
   1. **Oldindan tekshiruv (arzon, AI'siz):** fayl turi va hajmi, pHash orqali dublikat (foydalanuvchining oldingi isbotlari va umumiy baza bilan), EXIF vaqti.
   2. **Obyektiv manbalar:** challenge GitHub yoki Strava turida bo'lsa, API orqali tekshiriladi. AI chaqirilmaydi.
   3. **AI tekshiruvi:** vision modelga `verification_prompt` va kunlik kod beriladi. Javob qat'iy JSON formatida bo'ladi: `{decision, confidence, reason, detected_code}`.
4. Qaror qabul qilish:

| AI natijasi | Oddiy rejim | Stake rejimi |
|---|---|---|
| approve, confidence ≥ 0.8 | `approved` | `approved` |
| approve, confidence < 0.8 | `approved` | `needs_review` |
| reject, confidence ≥ 0.9 | `rejected` | `rejected` (kun tugaganda moderatorga ketadi, §6.3) |
| reject, confidence < 0.9 | `rejected` | `needs_review` |

5. Natija WebSocket/SSE yoki push/Telegram orqali foydalanuvchiga yuboriladi.

### 6.2. Aldashga qarshi himoya
- **Faqat ilova ichidagi kamera.** Stake rejimida galereyadan yuklash o'chiriladi.
- **Kunlik kod.** Har kuni har bir ishtirok uchun 4 belgili kod beriladi (masalan `K7X2`). U kodni qog'ozga yozib rasmga tushiradi. Kod server siridan HMAC orqali hisoblanadi, shuning uchun bazada saqlanmaydi va oldindan taxmin qilib bo'lmaydi.
- **pHash dublikat tekshiruvi.** Bir xil yoki juda o'xshash rasm qayta ishlatilsa aniqlanadi.
- **Tasodifiy selfie talabi** (v2): haftada 1–2 marta.
- **Shubhali akkauntlar:** rad etishlar ko'p bo'lsa, akkaunt qo'lda tekshiruvga o'tadi.

### 6.3. Adolat kafolatlari (garov platformada qolgani uchun majburiy)
Alohida apellyatsiya tugmasi o'rniga **avtomatik** himoya ishlaydi:
1. AI rad etsa, foydalanuvchi sababni ko'radi va **kun tugaguncha qayta yuborishi** mumkin.
2. Kun tugaganda, stake rejimida faqat AI rad etgan isbot qolgan bo'lsa, kun `awaiting_review` bo'ladi va isbot **avtomatik moderatorga** tushadi. Pul muzlatilgan holda qoladi.
3. AI ikkilansa (rad etish < 0.9 yoki tasdiqlash < 0.8 ishonch), isbot darhol moderatorga ketadi.
4. Moderator o'z isbotini tekshira olmaydi. Rad etishda sabab yozish majburiy. Qarori yakuniy.
5. Kelajakda: moderatorlar KPI'si platforma daromadiga bog'lanmaydi, AI va moderator qarorlari mosligi har oy tekshiriladi.

Bu qoidalar kodda domen darajasida yozilgan (`Participation.settle_day`, `verification/domain/policy.py`) va testlar bilan himoyalangan.

---

## 7. Ball va reyting

### 7.1. Ball formulasi
```
kunlik_ball   = 10 × difficulty × streak_koef
streak_koef   = 1.0 (1–6 kun) · 1.2 (7–13) · 1.5 (14–29) · 2.0 (30+)
yakun_bonus   = 50 × difficulty × duration_days / 7
stake_bonus   = yakun_bonus × 0.5  (faqat stake rejimida muvaffaqiyatli tugasa, ball sifatida, pul emas)
```

### 7.2. Reytinglar
| Scope | Redis kaliti | Izoh |
|---|---|---|
| Global | `lb:{period}:global` | |
| Tengdoshlar | `lb:{period}:age:2008` | tug'ilgan yil bo'yicha |
| Hudud | `lb:{period}:region:{region_id}` | viloyat/shahar |
| Do'stlar | Redis'da emas, so'rov paytida hisoblanadi | |
| Guruh | `lb:group:{group_id}` | |

- `period`: `weekly:2026-W39` · `season:2026-09` · `all`
- Asosiy reyting **haftalik va oylik mavsum** bo'yicha yuritiladi, shunda yangi foydalanuvchilarning ham imkoniyati bo'ladi.
- Guruhda **10 kishidan kam** bo'lsa, reyting ko'rsatilmaydi, faqat "sen N-o'rindasan" deb chiqadi.
- **Haqiqat manbai PostgreSQL** (`ScoreEvent` jadvali). Redis faqat kesh va istalgan paytda qayta qurilishi mumkin.

---

## 8. Ijtimoiy qism va bildirishnomalar

- **Do'stlar:** qo'shish/qabul qilish, do'stlar lentasi.
- **Accountability partner:** do'st isbotlaringizni ko'radi va reaksiya qoldiradi.
- **Telegram bot** (O'zbekiston uchun asosiy kanal):
  - Eslatmalar: 20:00 da "bugun isbot yubormading", 22:30 da "muddat tugashiga 1.5 soat qoldi".
  - Botdan to'g'ridan-to'g'ri isbot yuborish (v2).
  - AI natijasi haqida xabar.
- Web push va email ixtiyoriy.

---

## 9. Ma'lumotlar modeli

```
Region            id, name_uz, name_ru, parent_id (viloyat → shahar/tuman)

User              id, username (unique), phone (unique, nullable), email,
                  password_hash, birth_date (7+ tekshiruvi; reyting birth_year'ni oladi),
                  region_id → Region,
                  timezone (default 'Asia/Tashkent'), is_phone_verified,
                  telegram_chat_id, role (user|moderator|admin),
                  created_at

Friendship        id, requester_id, addressee_id, status (pending|accepted), created_at
                  UNIQUE(requester_id, addressee_id)

Challenge         id, title, description, category, duration_days, difficulty,
                  proof_types[], verification_prompt, is_template, created_by,
                  approval_status (draft|pending|approved|rejected),
                  stake_allowed, min_stake, max_stake, is_public, created_at

Group             id, name, challenge_id, owner_id, start_date, invite_code, created_at
GroupMember       group_id, user_id, joined_at

Participation     id, user_id, challenge_id, group_id (nullable),
                  mode (free|stake), stake_amount, difficulty, duration_days,
                  status (scheduled|active|completed|failed|cancelled),
                  start_date, current_streak, best_streak,
                  freezes_total, freezes_used, finished_on, created_at
                  UNIQUE(user_id, challenge_id) WHERE status IN (scheduled, active)

ParticipationDay  participation_id, date, status (pending|done|frozen|missed|awaiting_review)
                  PK(participation_id, date)          -- faqat jadvaldagi (ish) kunlar

participations.schedule_history (jsonb): [{since, week: 7 kun × [{key, title, minutes, required}]}]
                  -- o'tgan kunlar eski reja bo'yicha baholanadi

Plan              id, user_id, status (draft|started), answers (jsonb: goal, motivation,
                  current_level, obstacles, availability[7]), proposal (jsonb), challenge_id,
                  participation_id, created_at

Proof             id, participation_id, user_id, stake_mode, for_date, task_key, file_key, text_note,
                  phash, expected_code, submitted_at,
                  status (pending|approved|rejected|needs_review),
                  ai_decision, ai_confidence, ai_reason, ai_model, ai_detected_code,
                  reviewed_by, review_approved, review_note, reviewed_at
                  INDEX(participation_id, for_date, task_key), INDEX(user_id, phash)

Wallet            user_id (PK), available, locked, updated_at     -- kesh, ledger'dan qayta hisoblanadi

LedgerAccount     id, owner_user_id (nullable), type (user_available|user_locked|
                  platform_revenue|external)
LedgerEntry       id, transaction_id, account_id, amount (+/-), created_at
Transaction       id, user_id, kind (deposit|withdrawal|stake_lock|stake_release|
                  stake_forfeit), amount, reference_id (participation_id),
                  idempotency_key (unique), created_at

Payment           id, user_id, provider (payme|click|uzum), direction (in|out),
                  amount, provider_txn_id (unique), status, raw (jsonb), created_at

ScoreEvent        id, user_id, user_challenge_id, proof_id, points, reason, created_at

AuditLog          id, actor_id, action, entity, entity_id, data (jsonb), created_at
```

---

## 10. API (v1)

```
Auth
  POST /api/v1/auth/register            POST /api/v1/auth/login
  POST /api/v1/auth/refresh             POST /api/v1/auth/phone/verify
  POST /api/v1/auth/telegram/link

Onboarding va reja ("Menga reja tuz" yo'li)
  POST /api/v1/plans                              {answers} → AI draft reja
  GET  /api/v1/plans/{id}
  PATCH /api/v1/plans/{id}                        {schedule} (faqat draft)
  POST /api/v1/plans/{id}/start                   {mode, stake_amount?, start_date?}

Profil
  GET  /api/v1/me                       PATCH /api/v1/me
  GET  /api/v1/regions

Challenge
  GET  /api/v1/challenges?category=&stake_allowed=
  GET  /api/v1/challenges/{id}
  POST /api/v1/challenges                         (shaxsiy challenge)
  POST /api/v1/challenges/{id}/join               {mode, stake_amount?, group_id?, idempotency_key}
  GET  /api/v1/me/challenges?status=
  GET  /api/v1/me/challenges/{uc_id}              (kunlar kalendari, streak, freeze)
  POST /api/v1/me/challenges/{uc_id}/cancel       (faqat start_date'dan oldin)
  GET  /api/v1/me/challenges/{uc_id}/today        (bugungi vazifalar, kunlik kod, holat)
  PUT  /api/v1/me/challenges/{uc_id}/schedule     (ertadan; pulli rejimda faqat qiyinroq)

Isbot
  POST /api/v1/proofs/upload-url                  → {upload_url, file_key}
  POST /api/v1/proofs                             {uc_id, task_key, file_key?, text_note?, idempotency_key}
  GET  /api/v1/proofs/{id}
  GET  /api/v1/proofs/stream                      (SSE: holat o'zgarishlari)

Guruh va do'stlar
  POST /api/v1/groups                   POST /api/v1/groups/join {invite_code}
  GET  /api/v1/groups/{id}/feed
  POST /api/v1/friends/{user_id}        POST /api/v1/friends/{user_id}/accept

Reyting
  GET  /api/v1/leaderboard/{scope}?value=&period=weekly|season|all&limit=&offset=
       scope: global | age | region | friends | group
  GET  /api/v1/leaderboard/{scope}/me

Wallet
  GET  /api/v1/wallet                   GET /api/v1/wallet/transactions
  POST /api/v1/wallet/deposit           {amount, provider} → to'lov havolasi
  POST /api/v1/wallet/withdraw          {amount, card_token}
  POST /api/v1/webhooks/{provider}      (imzo bilan tekshiriladi)

Moderator
  GET  /api/v1/admin/proofs?status=needs_review
  POST /api/v1/admin/proofs/{id}/decision
  GET  /api/v1/admin/challenges?approval_status=pending
```

---

## 11. Arxitektura

```
            ┌────────────┐      ┌───────────────┐
 Brauzer ──▶│  Next.js   │─────▶│   Backend API │──▶ PostgreSQL
 Telegram ─▶│ (web app)  │      │               │──▶ Redis (kesh, reyting, navbat)
            └────────────┘      └──────┬────────┘
                   │ presigned PUT     │ task
                   ▼                   ▼
            ┌────────────┐      ┌───────────────┐     ┌──────────────────┐
            │ Blob / S3  │◀─────│ Celery worker │────▶│ AI (vision LLM)  │
            └────────────┘      │ Celery beat   │────▶│ GitHub / Strava  │
                                └──────┬────────┘     └──────────────────┘
                                       ▼
                               Payme / Click / Telegram Bot API
```

- **Backend: FastAPI + SQLAlchemy 2 + Alembic, DDD modular monolit.** Moderator paneli Next.js ichida quriladi.

### 11.1. DDD tuzilmasi

```
backend/src/pit/
  shared/            umumiy yadro: AggregateRoot, DomainEvent, Money, xatolar, UoW, MessageBus
  modules/
    identity/        User: ro'yxatdan o'tish (7 yoshdan), telefon, rol
    challenges/      Challenge (katalog), Schedule (haftalik jadval, vazifalar),
                     Participation (kalendar, streak, freeze, rejani o'zgartirish, natija)
    planning/        Onboarding javoblari, AI reja (Plan), 80% qoidasi → shaxsiy challenge
    verification/    Proof, AI qaror siyosati, kunlik kod, moderator ko'rigi
    wallet/          Wallet + double-entry ledger (deposit, lock, release, forfeit)
    ranking/         Ball formulasi, reyting kalitlari
    <modul>/
      domain/          sof Python: aggregate'lar, qoidalar, eventlar, repository interfeyslari
      application/     use-case'lar (command handler) va event handler'lar, portlar
      infrastructure/  SQLAlchemy repository, Redis, Celery, AI adapter  (keyingi bosqich)
      api/             FastAPI router'lar                               (keyingi bosqich)
  bootstrap.py       composition root: hamma modullarni bir-biriga ulaydi
```

**Qoidalar (`lint-imports` bilan avtomatik tekshiriladi):**
1. `domain` qatlami FastAPI, SQLAlchemy, Redis, Celery va Pydantic'ni import qila olmaydi.
2. Har bir modulda qatlamlar yo'nalishi: `api → infrastructure → application → domain`.
3. Modullar yo'nalishi: `ranking | wallet | verification | planning → challenges → identity`. Yuqoridagi modul pastdagisini hech qachon import qilmaydi. Kerak bo'lsa, **port** (interfeys) orqali ishlanadi, masalan challenges `StakeEscrow` portini e'lon qiladi, wallet uni amalga oshiradi.

**Modullar orasidagi aloqa:** command → handler → aggregate → domain event → boshqa modul handler'i. Masalan, `ParticipationFailed` eventi wallet'da `forfeit_stake` ni, `DayCompleted` eventi ranking'da ball berishni ishga tushiradi. Pul bilan bog'liq har bir handler idempotency kaliti bilan himoyalangan.

**Ma'lumotlar bazasi (✅ amalga oshirilgan):** har bir jadvalda `version` ustuni — optimistik qulflash. Bir vaqtda o'zgartirilgan yozuv `ConcurrencyConflict` beradi va MessageBus handler'ni yangi holat bilan 3 martagacha qayta ishga tushiradi. Faqat o'zgargan aggregate yoziladi (o'quvchilar bir-biriga xalaqit bermaydi). Pul himoyasi bazada ham: `wallets.available/locked >= 0` CHECK, `ledger_transactions.idempotency_key` UNIQUE, bitta challenge'da bitta ochiq ishtirok — qisman UNIQUE index. Migratsiyalar Alembic'da; 14 ta hudud seed migratsiyasi bilan yoziladi.

**Keyingi bosqich:** event'larni ishonchli yetkazish uchun **transactional outbox** qo'shiladi: event bazaga bir tranzaksiyada yoziladi, Celery uni yetkazadi.

- **Celery navbatlari:** `proofs` (AI), `scheduler` (kunlik job), `notifications`, `payments`. Ular alohida bo'lishi kerak, shunda AI sekinlashganda to'lovlar to'xtab qolmaydi.
- **AI provayderi abstraksiya orqali ulanadi** (`VerificationProvider` interfeysi), shunda model yoki provayderni almashtirish oson bo'ladi.
- **Docker Compose:** `web`, `api`, `worker`, `beat`, `postgres`, `redis`, `minio` (lokal S3).

---

## 12. Xavfsizlik va maxfiylik

- JWT access (15 daq) va refresh (httpOnly cookie). Login, join, deposit va proof endpoint'larida rate limiting.
- Isbot fayllari **private**, faqat qisqa muddatli signed URL orqali ochiladi.
- Reytingda faqat `username` va avatar ko'rinadi. Tug'ilgan yil va hudud faqat reyting filtri sifatida ishlatiladi.
- Platformadan 7 yoshdan boshlab hamma foydalanadi. Voyaga yetmaganlar profili standart holatda yopiq, rasmlari ochiq ko'rinmaydi.
- Barcha pul va moderator amallari `AuditLog`ga yoziladi.
- Shaxsiy ma'lumotlar O'zbekiston qonunchiligiga muvofiq saqlanishi kerak (serverlar joylashuvini tekshirish kerak).

---

## 13. Muvaffaqiyat metrikalari

- Challenge yakunlash darajasi (oddiy va stake rejimlarini alohida)
- D7 / D30 retention
- Kunlik faol foydalanuvchilar ichida isbot yuborganlar ulushi
- AI qarorlarining moderator bilan mos kelishi (AI aniqligi), moderatorga tushgan isbotlar ulushi
- Bitta isbotni tekshirishning o'rtacha narxi

---

## 14. Yo'l xaritasi

| Bosqich | Tarkib |
|---|---|
| **MVP** | Auth, hududlar, 5–10 ta shablon challenge, oddiy rejim, rasm va matnli isbot, AI pipeline + moderator paneli, kunlik job va freeze, haftalik reyting (global, yosh, hudud), Telegram eslatmalari |
| **v1.1 — Stake** | Wallet, ledger, Payme/Click, stake rejimi, kunlik kod, pHash, moderator navbati |
| **v1.2 — Together** | Do'stlar, guruh challenge'lari, jamoa streak'i, lenta |
| **v2** | GitHub/Strava integratsiyasi, shaxsiy challenge'lar, Telegram orqali isbot yuborish, homiylik challenge'lari, mobil ilova |

---

## 15. Ochiq qarorlar

1. ~~Muvaffaqiyatsizlikda pul qayerga ketadi?~~ ✅ Platformada qoladi (§5.4).
2. ~~Backend~~ ✅ FastAPI + DDD (§11.1).
3. **Yuridik tuzilma:** foydalanuvchi pulini ushlab turish uchun qanday litsenziya yoki shartnoma kerak. Payme/Click bilan ishlash uchun yuridik shaxs. **Stake funksiyasini ishga tushirishdan oldin yurist maslahati shart.**
4. **Qisman muvaffaqiyat:** 30 kundan 28 kun bajarilsa (freeze'lar tugagan bo'lsa), pulning bir qismi qaytarilsinmi yoki "hammasi yoki hech narsa" qoidasi qoladimi? Hozirgi dizayn: hammasi yoki hech narsa, lekin freeze'lar bilan.
5. ~~Voyaga yetmaganlar pulli rejimda qatnashadimi?~~ ✅ Ha, yosh cheklovi yo'q: bolalar uchun pulni ota-ona to'laydi va bu ota-onalar uchun motivatsiya vositasi. Faqat telefon tasdig'i talab qilinadi. (Yuridik maslahatda shu holatni alohida so'rash kerak, 3-band.)
