# PIT — Personal Improvement Together

Maqsadlarni har kungi odatga aylantiruvchi platforma: AI reja, isbot, murabbiy, garov va reyting.
Mahsulot tavsifi: [docs/PRD.md](docs/PRD.md).

## Ishga tushirish (lokal)

```bash
# 1. Postgres + Redis (portlar 5433 / 6380)
docker compose up -d --wait

# 2. Backend — http://localhost:8000  (API hujjati: /docs)
cd backend
uv sync
cp .env.example .env          # PIT_DAILY_CODE_SECRET va PIT_JWT_SECRET ni o'zgartiring
uv run alembic upgrade head
uv run python -m pit.cli seed # 8 ta tayyor challenge
uv run uvicorn pit.main:app --reload

# 3. Frontend — http://localhost:3100
cd frontend
pnpm install
pnpm dev --port 3100
```

Moderator qilish: `uv run python -m pit.cli make-moderator <username>`

**Pulli funksiyalar hozircha o'chiq** (`PIT_STAKES_ENABLED=false`): garov rejimi va hamyon
yashirin, platforma to'liq bepul. Keyin yoqish uchun `.env` da `PIT_STAKES_ENABLED=true`
(avval Payme/Click integratsiyasi va yurist maslahati kerak).

AI kaliti bo'lmasa (`PIT_AI_PROVIDERS=` bo'sh) isbotlar avtomatik tasdiqlanadi, rejalar
shablondan tuziladi. Haqiqiy AI: `PIT_AI_PROVIDERS=gemini,groq` va har birining kaliti
(`PIT_GEMINI_API_KEY`, `PIT_GROQ_API_KEY`; OpenAI/Azure ham bor). Provayderlar galma-gal
ishlaydi; biri band yoki limitga ursa, so'rov darhol keyingisiga o'tadi va u 1 daqiqa dam oladi.
Isbot uchun rasm tushunadigan model (`*_MODEL`), reja uchun matn modeli (`*_PLAN_MODEL`).
Jonli tekshiruv: `uv run python -m pit.cli ai-check`.

## Production (bitta server)

Talab: Docker o'rnatilgan Linux server (2 vCPU, 4 GB RAM yetadi), domenning A-yozuvi server IP'siga.

```bash
cp deploy/.env.prod.example deploy/.env.prod   # DOMAIN, parollar, sirlar, Eskiz, AI kalitini to'ldiring
docker compose -f docker-compose.prod.yml --env-file deploy/.env.prod up -d --build
```

Nima ishga tushadi: Postgres, Redis, migratsiya + katalog, API, Celery worker (AI tekshiruv),
Celery beat (00:15 kunlarni yopish, 08:00/20:00 murabbiy xabarlari), Next.js, Caddy
(Let's Encrypt orqali avtomatik HTTPS, `/api` → backend, qolgani → frontend).

Xavfsizlik: login, ro'yxatdan o'tish, SMS, isbot va AI reja uchun urinishlar cheklangan;
parol Telegram bot (yoki SMS) orqali tiklanadi; `PIT_ENV=production` da test to'lov tugmasi o'chadi.

Hali ulanmagan: Payme/Click (webhook `Deposit` buyrug'ini chaqiradi), pulni kartaga yechish.

### Telegram bot

Murabbiy xabarlari (ertalabki reja, kechki eslatma, tabriklar) Telegram'ga ham boradi,
isbotni esa botning o'zida yuborsa bo'ladi: `/bugun` → vazifa → rasm. Buyruqlar: `/bugun`,
`/holat`, `/yordam`, `/stop`. Foydalanuvchi saytda **Profil → Telegram'ni ulash** orqali
bir martalik (10 daqiqalik) havola bilan ulaydi.

1. @BotFather'da `/newbot` — token va username oling.
2. `deploy/.env.prod` da `PIT_TELEGRAM_BOT_TOKEN`, `PIT_TELEGRAM_BOT_USERNAME` va
   `PIT_TELEGRAM_WEBHOOK_SECRET` (tasodifiy satr) ni to'ldiring.
3. Deploy qiling — webhook `migrate` bosqichida avtomatik ro'yxatdan o'tadi
   (qo'lda: `docker compose -f docker-compose.prod.yml run --rm migrate python -m pit.cli telegram-setup`).

Lokalda: `backend/.env` ga test botning token va username'ini yozing (`PIT_TELEGRAM_MODE=polling`)
va API'ni qayta ishga tushiring — ochiq URL kerak emas. Token bo'sh bo'lsa, bot o'chiq va
saytda Telegram tugmalari ko'rinmaydi.

### Google orqali kirish

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → **Create credentials →
   OAuth client ID** → turi **Web application**.
2. **Authorized JavaScript origins**: `https://pit.uz` (lokalda `http://localhost:3100`).
   Redirect URI kerak emas.
3. Client ID'ni `PIT_GOOGLE_CLIENT_ID` ga yozing. Bo'sh bo'lsa, Google tugmasi ko'rinmaydi.

Yangi Google foydalanuvchisi tug'ilgan sana, hudud va shartlarga rozilikni to'ldiradi
(`/register/google`); keyingi safar bir bosishda kiradi. Bunday akkauntda parol yo'q.

### Telefonni tasdiqlash

Telefon Telegram bot orqali bepul tasdiqlanadi: botda «📱 Raqamni yuborish» — Telegram
foydalanuvchining o'z raqamini yuboradi (begona kontakt qabul qilinmaydi). Parolni tiklash
kodi ham botga keladi. SMS (`PIT_SMS_PROVIDER=eskiz`) faqat zaxira.

### Zaxira (backup)

`backup` servisi har kuni baza (`db-YYYY-MM-DD.dump`) va isbot rasmlari (`storage-YYYY-MM-DD.tar.gz`)
nusxasini `backups` volume'iga yozadi, 14 kundan eskisini o'chiradi (`BACKUP_KEEP_DAYS`).
Nusxalarni serverdan tashqariga ham ko'chirib turing (masalan boshqa serverga `rsync`) —
disk buzilsa, bir joydagi zaxira yordam bermaydi.

```bash
# Ro'yxat
docker compose -f docker-compose.prod.yml exec backup ls -lh /backups

# Tiklash (DIQQAT: joriy ma'lumotlar almashtiriladi). Avval API/worker'ni to'xtating:
docker compose -f docker-compose.prod.yml stop api worker beat
docker compose -f docker-compose.prod.yml exec backup \
  pg_restore -h postgres -U pit -d pit --clean --if-exists --no-owner /backups/db-2026-09-25.dump
docker compose -f docker-compose.prod.yml run --rm --entrypoint sh -v pit_storage:/restore backup \
  -c 'tar -xzf /backups/storage-2026-09-25.tar.gz -C /restore'
docker compose -f docker-compose.prod.yml start api worker beat
```

(`pit_storage` — volume nomi, `docker volume ls` bilan tekshiring.) Reyting Redis'da turadi va
AOF bilan saqlanadi; yo'qolsa ham ballar bazada qoladi.

### Huquqiy sahifalar

`/terms` va `/privacy` — ro'yxatdan o'tishda rozilik majburiy, versiyasi va vaqti `users` jadvalida
saqlanadi. Matnni o'zgartirsangiz, `CURRENT_TERMS_VERSION` (`identity/domain/user.py`) va sahifadagi
sanani yangilang. Ishga tushirishdan oldin matnni yuristga ko'rsating va `support@pit.uz` ni
haqiqiy manzilga almashtiring.

## Tekshiruvlar

```bash
cd backend && uv run pytest && uv run mypy && uv run ruff check . && uv run lint-imports
cd frontend && npx tsc --noEmit && pnpm lint && pnpm build
```

Tuzilma: [backend/README.md](backend/README.md).
