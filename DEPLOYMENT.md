# Vercel Deployment Guide (RoomRent Full Stack App)

Ye project Django 5.2 + Channels (WebSocket) + PostgreSQL par bana hai.
Vercel ab Django ko **zero-configuration** support karta hai:

* Vercel `manage.py` detect karta hai, `DJANGO_SETTINGS_MODULE` nikaalta hai aur
  entrypoint `WSGI_APPLICATION` / `ASGI_APPLICATION` se resolve karta hai
  (is project me ASGI use hota hai kyunki chat + notifications WebSocket par hain).
* Build ke waqt Vercel khud `collectstatic` chalata hai aur `STATIC_ROOT` ko
  `public/<STATIC_URL>/` par override karke files **Vercel CDN** se serve karta hai.
* `vercel.json` me koi `builds`/`routes` likhne ki zarurat nahi (sirf `maxDuration`
  set karne ke liye `functions` block use kiya gaya hai).

---

## 1. Vercel par zaroori Environment Variables

Vercel → Project → **Settings → Environment Variables** (Production + Preview dono me):

| Variable | Value | Zaroori? |
|---|---|---|
| `SECRET_KEY` | 50+ random characters | **Haan** (iske bina app start nahi hota) |
| `DEBUG` | `False` | **Haan** |
| `DB_NAME` | database name | **Haan** |
| `DB_USER` | database user | **Haan** |
| `DB_PASSWORD` | database password | **Haan** |
| `DB_HOST` | cloud Postgres host (Neon / Supabase) | **Haan** |
| `DB_PORT` | `5432` (Supabase pooler ho to `6543`) | **Haan** |
| `DB_SSLMODE` | `require` | Recommended |
| `EXTRA_ALLOWED_HOSTS` | `myapp.com,www.myapp.com` | Custom domain ho to |
| `REDIS_URL` | Upstash Redis URL | WebSocket multi-instance ke liye |
| `AWS_STORAGE_BUCKET_NAME` + `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` + `AWS_S3_ENDPOINT_URL` + `AWS_S3_CUSTOM_DOMAIN` | cloud media storage | Image uploads ke liye |

SECRET_KEY generate karne ke liye:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g;print(g())"
```

Local development ke liye `.env.example` ko copy karke `.env` banao.

---

## 2. Database

Vercel serverless hai, isliye **local Postgres (`localhost`) kaam nahi karega**.
Neon / Supabase / Vercel Postgres ka **pooled connection string** use karo.

Migrations Vercel build ke waqt **automatically nahi chalti**. Apne machine se
cloud DB ke against chalao:

```bash
# .env me cloud DB ki values daal kar
python manage.py migrate
python manage.py createsuperuser

# purane local data ko cloud DB me le jaana ho to
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > data.json
# (cloud DB par) python manage.py loaddata data.json
```

---

## 3. Media (image) uploads — important

Vercel Functions ka filesystem **read-only** hai, isliye:

* Repo me pehle se padi files (`media/**`) production me `/media/...` se serve hoti
  hain (`SomeNew/urls.py` me route hai) — jo pehle se commit hain wo dikhengi.
* **Naye uploads** (profile photo, post images, maintenance photos) disk pe save
  nahi ho sakte → cloud storage chahiye:

```bash
pip install "django-storages[s3]" boto3
```

Phir Vercel me `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, aur (Supabase/R2 ke liye) `AWS_S3_ENDPOINT_URL`,
`AWS_S3_CUSTOM_DOMAIN` set kar do — `settings.py` khud S3 storage on kar lega.
`requirements.txt` me se `django-storages` wali line uncomment karni hogi.

> Vercel Functions ka request body limit **4.5 MB** hai, isse badi image upload
> karne par `413 FUNCTION_PAYLOAD_TOO_LARGE` milega.

---

## 4. WebSockets (chat + live notifications)

Vercel Functions WebSocket support karte hain (Python/ASGI + Django Channels).
Is project me `SomeNew/asgi.py` ASGI entrypoint hai aur consumers
`homepage/consumers.py` me hain.

* `InMemoryChannelLayer` sirf **ek hi function instance** ke andar kaam karta hai.
  Production me multiple instances bante hain, isliye:

```bash
pip install channels-redis
# requirements.txt me se channels-redis uncomment karo
```
aur Vercel me `REDIS_URL` (Upstash Redis — Vercel Marketplace se) set karo.

* Ek WebSocket connection usi function instance se **max duration** tak juda rehta
  hai (`vercel.json` me `maxDuration: 60`), isliye client side reconnect logic
  hone chahiye.

---

## 5. Deploy kaise karein

1. Saara code GitHub par push karo (branch: `main`).
2. Vercel → **Add New → Project** → repo import karo (`GenZpreparation/Rapid-Room-Project`).
3. Upar wale **Environment Variables** add karo (deploy se pehle).
4. **Deploy** dabao — Vercel khud dependencies install karega, `collectstatic`
   chalayega aur ASGI app deploy karega.
5. Deploy ke baad `https://<project>.vercel.app/admin/` kholo aur check karo.
6. Migrations apne local machine se cloud DB par chalao (step 2 dekho).

CLI se deploy karna ho to:

```bash
npm i -g vercel
vercel          # preview deploy
vercel --prod   # production deploy
```

---

## 6. Local development

```bash
python -m venv env
env\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

`daphne` install hai, isliye `runserver` ASGI dev-server chalata hai —
WebSocket (chat + notifications) local pe bhi test ho sakte hain.
