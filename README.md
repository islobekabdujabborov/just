# AvoBook

Audiokitob ijtimoiy tarmog'i: React/Vite frontend va Django REST API.

## Mahalliy ishga tushirish

Backend uchun terminalda:

```powershell
python -m pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py runserver 8000
```

Ikkinchi terminalda frontend:

```powershell
npm install
npm run dev
```

Frontend API so'rovlarini lokal Django serveriga proxy qiladi. Kerak bo'lsa, `VITE_API_URL` orqali API manzilini o'zgartiring.

## Railway deploy

Railway loyihasiga GitHub repository'ni ulang. Root'dagi `Dockerfile` frontend build va Django serverini bitta service sifatida tayyorlaydi; migratsiyalar container ishga tushganda bajariladi.

1. Railway'da PostgreSQL service yarating va app service uchun `DATABASE_URL`ni PostgreSQL service'ning `DATABASE_URL` qiymatiga ulang.
2. App service Variables bo'limida `SECRET_KEY`ni maxfiy, tasodifiy qiymat bilan belgilang. Masalan, lokalda `python -c "import secrets; print(secrets.token_urlsafe(50))"` buyrug'i bilan yaratish mumkin.
3. `DEBUG` qiymatini `False` qiling. `RAILWAY_PUBLIC_DOMAIN` Railway tomonidan berilganda Django uni ruxsat etilgan host sifatida qo'shadi.
4. Deploy qiling va Railway'dan public domain yarating.

Railway diskidagi yuklangan media fayllar deploylar orasida saqlanmaydi. Uploadlar ishlatilsa, app service'ga volume ulang va mount path'ni `/app/backend/media` qiling. `MEDIA_ROOT` shu manzilga default bo'ladi.

API manzil `/api/`, admin `/admin/`.
