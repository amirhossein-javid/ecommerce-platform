# E-commerce frontend

رابط کاربری فروشگاه با Next.js App Router، TypeScript و Tailwind CSS. پیاده‌سازی
فعلی شامل کاتالوگ و جزئیات محصول، احراز هویت و پروفایل، مدیریت آدرس، سبد مهمان
و مشتری با merge، checkout، آغاز/نتیجهٔ پرداخت و تاریخچه و جزئیات سفارش‌های
حساب مشتری و ویترین صفحهٔ اصلی فروشگاه (Phase 6.1) است.

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

برای رسانه‌ای که در توسعه روی Django نگهداری می‌شود، Compose متغیر فقط‌سرور
`DJANGO_PUBLIC_MEDIA_URL` را به `http://localhost:8000/media/` تنظیم می‌کند تا
URL ساخته‌شده با hostname داخلی `web` پیش از رندر برای مرورگر محلی نگاشت شود.
URL رسانه‌های storage خارجی بدون تغییر باقی می‌ماند.

برای درگاه عمومی‌ای که Django در پاسخ آغاز پرداخت `payment_url` برمی‌گرداند،
مبدأ دقیق مقصد باید در متغیر فقط‌سرور `PAYMENT_REDIRECT_ALLOWED_ORIGINS` قرار
گیرد (چند مبدأ با ویرگول جدا می‌شوند). این مقدار برای شناسهٔ صورتحساب Bale لازم
نیست. مسیر بازگشت عمومی رابط کاربری
`/checkout/payment-return/<order-id>/<payment-id>` است؛ تنظیم درگاه برای بازگشت
به این مسیر، بخشی از پیکربندی همان provider است و نتیجهٔ نهایی همچنان فقط از
Django خوانده می‌شود.

Compose در نبود تنظیم صریح provider به `UnavailablePaymentGateway` برمی‌گردد و
شبیه‌ساز پرداخت داخلی ندارد. فایل نمونهٔ ریشه Bale را انتخاب می‌کند، اما تست
واقعی آن همچنان به credential، webhook عمومی HTTPS و اجرای Mini App بله نیاز
دارد؛ callback مرورگر یا SDK به‌تنهایی نشانهٔ موفقیت پرداخت نیست.

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
docker compose run --rm --no-deps frontend npm test
docker compose run --rm --no-deps frontend npm run build
```
