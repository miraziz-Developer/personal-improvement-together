# PIT'ni tekin joylashtirish

| Qism | Qayerda | Narxi |
|---|---|---|
| Sayt (Next.js) | Vercel | doim tekin |
| Ma'lumotlar bazasi | Neon Postgres | doim tekin (0.5 GB) |
| API + Telegram bot + eslatmalar + Redis + isbot rasmlari | Azure B1s server (`rg-pit` / `pit-vm`) | Azure for Students: 12 oy tekin |
| HTTPS va manzil | Caddy + sslip.io | tekin |

Server faqat API'ni ishlatadi (`docker-compose.lite.yml`): Celery yo'q, kunlik ishlar va AI
tekshiruvi API ichida yuradi (`PIT_INLINE_TASKS=true`), sayt Vercel'da, baza Neon'da.

## 1. Neon (baza)

1. https://neon.tech → GitHub bilan kiring → **New project** (region: Frankfurt yoki eng yaqini).
2. **Connection string**ni nusxalang. Boshidagi `postgresql://` ni `postgresql+psycopg://`
   ga almashtiring, oxirida `?sslmode=require` bo'lsin. Bu — `PIT_DATABASE_URL`.

## 2. Server (Azure)

```sh
ssh -i ~/.ssh/pit_azure pit@<IP>
sudo sh deploy/setup-vm.sh           # swap + Docker, bir marta
```

Kod serverga kompyuterdan yuboriladi (repo private):

```sh
rsync -az --delete -e "ssh -i ~/.ssh/pit_azure" \
  --exclude .venv --exclude .storage --exclude '.*_cache' --exclude .env \
  backend docker-compose.lite.yml deploy pit@<IP>:~/pit/
```

Serverda `~/pit/deploy/.env.lite` (namuna: `.env.lite.example`):

- `DOMAIN` — IP'ning nuqtalari chiziqcha bilan: `20.1.2.3` → `20-1-2-3.sslip.io`
- `PIT_PUBLIC_BASE_URL=https://<DOMAIN>`
- `PIT_CORS_ORIGINS` va `PIT_WEB_URL` — Vercel manzili
- maxfiy kalitlar: `python3 -c "import secrets; print(secrets.token_hex(32))"`

Ishga tushirish va yangilash (har safar kod yuborilgandan keyin):

```sh
cd ~/pit && docker compose -f docker-compose.lite.yml --env-file deploy/.env.lite up -d --build
curl https://<DOMAIN>/health
```

## 3. Vercel (sayt)

1. https://vercel.com → GitHub bilan kiring → **Add New → Project** → repo'ni tanlang.
2. **Root Directory**: `frontend`.
3. **Environment Variables**: `NEXT_PUBLIC_API_URL=https://<DOMAIN>`.
4. **Deploy**. Manzil (masalan `https://pit-app.vercel.app`) serverdagi `PIT_CORS_ORIGINS` va
   `PIT_WEB_URL` ga yoziladi, keyin serverda `up -d` qayta.

`main` ga har push'da Vercel saytni o'zi yangilaydi.

## Bilish kerak

- Azure tekin tarifi: B1s server oyiga 750 soat, 64 GB P6 disk — 12 oy. Kredit ($100) tugasa,
  obuna to'xtaydi va bu server ham o'chadi: boshqa pullik resurslarni kerak bo'lmaganda
  to'xtatib qo'ying (Stop/Deallocate).
- Baza Neon'da — server almashsa ham ma'lumot joyida qoladi. Isbot rasmlari serverning
  `storage` volume'ida: serverni o'chirishdan oldin nusxa oling.
- AI kalitlari bepul tarifda bo'lsa, provayder ma'lumotdan o'qitish uchun foydalanishi mumkin.
