# PIT'ni tekin joylashtirish

| Qism | Qayerda | Narxi |
|---|---|---|
| Sayt (Next.js) | Vercel | doim tekin |
| API + Telegram bot + eslatmalar + Postgres + Redis + isbot rasmlari + kunlik zaxira | Azure B1s server (`rg-pit` / `pit-vm`) | Azure for Students: 12 oy tekin |
| API manzili | `pit-uz.indiasouthcentral.cloudapp.azure.com` (Azure'ning tekin DNS nomi) + Caddy HTTPS | tekin |
| Sayt manzili | `pit-uz.vercel.app` (Vercel loyiha nomi) | tekin |

Server `docker-compose.lite.yml` bilan ishlaydi: Celery yo'q, kunlik ishlar va AI tekshiruvi API
ichida yuradi (`PIT_INLINE_TASKS=true`); Postgres ham shu serverda, 1 GB ga moslab sozlangan.
Sayt Vercel'da.

## 1. Server (Azure)

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

- `DOMAIN=pit-uz.indiasouthcentral.cloudapp.azure.com` — server IP'siga Azure bergan tekin nom
  (`az network public-ip update -g rg-pit -n pit-vmPublicIP --dns-name pit-uz`)
- `PIT_PUBLIC_BASE_URL=https://<DOMAIN>`
- `PIT_CORS_ORIGINS` va `PIT_WEB_URL` — Vercel manzili
- `POSTGRES_PASSWORD` va boshqa maxfiy kalitlar: `python3 -c "import secrets; print(secrets.token_hex(32))"`

Ishga tushirish va yangilash (har safar kod yuborilgandan keyin):

```sh
cd ~/pit && docker compose -f docker-compose.lite.yml --env-file deploy/.env.lite up -d --build
curl https://<DOMAIN>/health
```

## 2. Vercel (sayt)

1. https://vercel.com → GitHub bilan kiring → **Add New → Project** → repo'ni tanlang,
   **Project Name**: `pit-uz` (manzil `pit-uz.vercel.app` bo'ladi).
2. **Root Directory**: `frontend`.
3. **Environment Variables**: `NEXT_PUBLIC_API_URL=https://<DOMAIN>`.
4. **Deploy**. Manzil (masalan `https://pit-app.vercel.app`) serverdagi `PIT_CORS_ORIGINS` va
   `PIT_WEB_URL` ga yoziladi, keyin serverda `up -d` qayta.

`main` ga har push'da Vercel saytni o'zi yangilaydi.

## Telegram Mini App

Bot tugmalari va pastdagi «PIT» menyu tugmasi saytni Telegram ichida ochadi (`/tg`).
Har deploy'da `migrate` webhook'ni va menyu tugmasini `PIT_WEB_URL` ga qarab o'zi sozlaydi —
BotFather'da hech narsa qilish shart emas. `PIT_WEB_URL` https bo'lishi shart.

## Haqiqiy domen (ixtiyoriy)

GitHub Student Developer Pack (https://education.github.com/pack) talabalarga 1 yilga tekin
`.me` (Namecheap) yoki `.tech` domen beradi. Olingach: domenni Vercel'ga ulang, API uchun
`api.<domen>` A-yozuvini server IP'siga yo'naltiring va `.env.lite` dagi manzillarni almashtiring.

## Bilish kerak

- Azure tekin tarifi: B1s server oyiga 750 soat, 64 GB P6 disk — 12 oy. Kredit ($100) tugasa,
  obuna to'xtaydi va bu server ham o'chadi: boshqa pullik resurslarni kerak bo'lmaganda
  to'xtatib qo'ying (Stop/Deallocate).
- Zaxira: `backup` servisi har kuni baza (`db-<sana>.dump`) va rasmlarni (`storage-<sana>.tar.gz`)
  `backups` volume'iga yozadi, 14 kun saqlaydi. Ular shu serverda turadi — vaqti-vaqti bilan
  kompyuterga ham ko'chirib oling:
  `ssh pit-vm 'docker run --rm -v pit-lite_backups:/b alpine tar -C /b -cf - .' > pit-backups.tar`
- Serverni almashtirish: yangi serverda `up -d`, keyin oxirgi `db-*.dump` ni
  `pg_restore -h postgres -U pit -d pit --clean` bilan tiklash.
- AI kalitlari bepul tarifda bo'lsa, provayder ma'lumotdan o'qitish uchun foydalanishi mumkin.
