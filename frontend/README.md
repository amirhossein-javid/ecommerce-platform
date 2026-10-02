# E-commerce frontend

پایهٔ رابط کاربری فروشگاه با Next.js App Router، TypeScript و Tailwind CSS.

## اجرای محلی با Docker

مسیر اصلی توسعه از ریشهٔ مخزن اجرا می‌شود و به نصب Node.js یا npm روی میزبان
نیازی ندارد:

```bash
docker compose up --build
```

رابط کاربری در `http://localhost:3000` در دسترس است. سورس `frontend/` برای
reload توسعه‌ای bind mount می‌شود، اما `node_modules` و `.next` در volumeهای
نام‌دار Docker نگهداری می‌شوند. Compose برای تشخیص مطمئن تغییر فایل‌ها روی
Docker Desktop، dev server را با Webpack و polling یک‌ثانیه‌ای اجرا می‌کند؛
production build همچنان از تنظیم پیش‌فرض Next.js استفاده می‌کند.

Compose متغیر فقط-سرور `DJANGO_API_URL` را به `http://web:8000` تنظیم می‌کند؛
`web` نام سرویس Django در شبکهٔ Compose است. این مقدار نباید با پیشوند
`NEXT_PUBLIC_` در اختیار مرورگر قرار گیرد.

## اجرای مستقل اختیاری

برای اجرای frontend خارج از Docker به Node.js 24 LTS و npm نیاز است:

```bash
cp .env.example .env.local
npm install
npm run dev
```

در این حالت مقدار نمونهٔ `DJANGO_API_URL=http://localhost:8000` مناسب است.

## بررسی کیفیت

```bash
docker compose run --rm --no-deps frontend npm run lint
docker compose run --rm --no-deps frontend npm run typecheck
```
