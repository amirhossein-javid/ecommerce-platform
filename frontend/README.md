# رابط فروشگاه نقش‌جهان

رابط کاربری فروشگاه با Next.js App Router، TypeScript و Tailwind CSS. پیاده‌سازی
فعلی تمام مسیر مشتری از ویترین و کاتالوگ تا حساب کاربری، سبد، checkout، پرداخت
و تاریخچه و جزئیات سفارش را پوشش می‌دهد. قرارداد API و مرزهای امنیتی تفصیلی در
[`FRONTEND_HANDOFF.md`](../FRONTEND_HANDOFF.md) ثبت شده‌اند.

## قابلیت‌های فعلی

- صفحهٔ اصلی server-rendered با دسته‌بندی‌ها و محصولات واقعی کاتالوگ؛
- فهرست و جزئیات محصول، جست‌وجو، فیلتر، مرتب‌سازی و صفحه‌بندی؛
- ثبت‌نام، ورود/خروج، پروفایل و مدیریت کامل آدرس‌ها؛
- سبد مهمان و مشتری، merge صریح پس از ورود، تغییر تعداد و حذف؛
- checkout، انتخاب آدرس، آغاز و بازگشت پرداخت و نمایش وضعیت معتبر Django؛ و
- تاریخچهٔ صفحه‌بندی‌شده و جزئیات سفارش‌های متعلق به مشتری و ادامهٔ پرداخت فقط
  برای سفارش واجد شرایط طبق قرارداد backend؛ و
- نظرها و امتیازهای تأییدشدهٔ محصول، فرم ثبت نظر مشتری، نمایش وضعیت بررسی و
  حذف با تأیید برای ثبت مجدد؛ و
- داشبورد متمرکز `/dashboard` با بخش‌های `/dashboard/orders` و
  `/dashboard/reviews` برای شاخص‌های واقعی عملیات، تکمیل سفارش، بررسی، فیلتر،
  تأیید/رد نظرها و مدیریت پاسخ رسمی فروشگاه با نشست HttpOnly مستقل اپراتور.

کارت مشترک محصول در خانه و همهٔ حالت‌های فهرست کاتالوگ، میانگین و تعداد
نظرهای تأییدشده را نمایش می‌دهد و برای محصول بدون نظر تأییدشده عبارت
«بدون امتیاز» را نشان می‌دهد. fetch فهرست محصولات برای جلوگیری از امتیاز
منقضی پس از moderation یا حذف review به‌صورت `no-store` انجام می‌شود.

ساختار App Router تا جای ممکن server-first است و Client Component فقط برای
تعامل واقعی استفاده می‌شود. مرورگر مستقیماً JWT یا `X-Cart-Token` را در اختیار
JavaScript ندارد؛ BFF آن‌ها را در cookieهای HttpOnly نگه می‌دارد، mutationها را
از نظر origin محافظت می‌کند و پاسخ‌های شخصی را `private/no-store` برمی‌گرداند.

## هویت بصری و قواعد رابط

صفحهٔ اصلی و componentهای مشترک منبع طراحی نقش‌جهان هستند. layout سراسری فارسی
و RTL است و فونت متغیر Vazirmatn به‌صورت محلی بارگذاری می‌شود. tokenهای
`globals.css` زمینه و سطح عاجی، آبی ایرانی/lapis، فیروزه‌ای و طلایی محدود،
رنگ‌های معنایی، focus، سایهٔ کارت و الگوی اختیاری نقش را تعریف می‌کنند.

در توسعهٔ صفحات جدید، header، footer، page header، کارت‌ها، فرم‌ها و وضعیت‌های
مشترک را بازاستفاده کنید؛ طراحی باید mobile-first و در عرض‌های 360 و 390 پیکسل
قابل استفاده باشد. قیمت، تصویر، موجودی، وضعیت سفارش و هر ادعای تجاری باید از
Django بیاید. تخفیف، امتیاز، تضمین ارسال یا دادهٔ ساختگی نمایش ندهید. مبالغ API
رشتهٔ صحیح ریال هستند و فقط برای نمایش، بدون گردکردن، به تومان تبدیل می‌شوند.

## نظر و امتیاز محصول

صفحهٔ جزئیات محصول میانگین و تعداد نظرهای تأییدشده و تازه‌ترین نظرهای عمومی را
نمایش می‌دهد. مشتری واردشده می‌تواند یک امتیاز صحیح از ۱ تا ۵ و متن اجباری ثبت
کند، وضعیت `در انتظار بررسی`، `تأییدشده` یا `تأیید نشد` را ببیند و نظر خود را با
تأیید حذف کند. ویرایش وجود ندارد؛ پس از حذف، ثبت دوباره با وضعیت در انتظار
ممکن است. BFF پاسخ شخصی را `private/no-store` نگه می‌دارد و mutationها را با
بررسی origin محافظت می‌کند. carousel ثابت صفحهٔ اصلی مستقل از این سامانه است.
هر نظر حداکثر یک پاسخ رسمی دارد و پاسخ فقط کنار نظر تأییدشده نمایش داده می‌شود.
داشبورد مدیریت از cookieهای جداگانهٔ اپراتور و BFFهای `private/no-store` استفاده
می‌کند؛ مجوزهای نهایی هر عملیات را Django بررسی می‌کند و `is_staff` به‌تنهایی
کافی نیست.

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

## کانتینر production

مرحلهٔ نهایی `Dockerfile` یک خروجی standalone بهینهٔ Next.js می‌سازد، فقط
فایل‌های runtime را در image نهایی نگه می‌دارد و سرور را با کاربر غیر-root
`node` اجرا می‌کند. نصب dependencyها با `npm ci` و `package-lock.json` انجام
می‌شود:

```bash
docker build --target production -t naghsh-frontend ./frontend
docker run --rm -p 3000:3000 \
  -e DJANGO_API_URL=http://django.internal:8000 \
  -e DJANGO_PUBLIC_MEDIA_URL=https://media.example.com/ \
  naghsh-frontend
```

`DJANGO_API_URL` برای همهٔ فراخوانی‌های server-to-server به Django الزامی است
و نباید با پیشوند `NEXT_PUBLIC_` منتشر شود. `DJANGO_PUBLIC_MEDIA_URL` فقط وقتی
لازم است که URL رسانهٔ داخلی Django باید به مبدأ عمومی مرورگر نگاشت شود.
`PAYMENT_REDIRECT_ALLOWED_ORIGINS` نیز فقط برای مبدأهای دقیق HTTPS درگاه‌هایی
است که `payment_url` برمی‌گردانند و برای شناسهٔ صورتحساب Bale خالی می‌ماند.
`PORT` اختیاری است و مقدار پیش‌فرض آن `3000` است. image مقدارهای
`NODE_ENV=production` و `HOSTNAME=0.0.0.0` را تعیین می‌کند تا cookieهای BFF در
production دارای `Secure` باشند و standalone server روی رابط کانتینر گوش کند.

مسیر `GET /api/health` پاسخ ثابت `{"status":"ok"}` و
`Cache-Control: no-store` می‌دهد. این liveness probe عمداً Django، PostgreSQL،
نشست کاربر و refresh-token را لمس نمی‌کند. Docker healthcheck همین مسیر را روی
loopback کانتینر بررسی می‌کند. readiness کل فروشگاه باید جداگانه اتصال واقعی
frontend به Django و readiness خود Django را کنترل کند.

TLS در image خاتمه نمی‌یابد. ingress باید HTTPS و hostهای مجاز را enforce کند،
درخواست مرورگر و BFF را same-origin نگه دارد و scheme/host اصلی را بدون پذیرش
header جعلی کاربر به Next.js برساند. هیچ Compose تولیدی اضافه نشده است، چون
دامنه، ingress، PostgreSQL و media storage تصمیم‌های محیط استقرار هستند.
Compose ریشه همچنان فقط توسعه‌ای است و برای frontend مرحلهٔ `development` را
می‌سازد.

## بررسی کیفیت

```bash
docker compose run --rm --no-deps frontend npm run lint
docker compose run --rm --no-deps frontend npm run typecheck
docker compose run --rm --no-deps frontend npm test
docker compose run --rm --no-deps frontend npm run build
```
