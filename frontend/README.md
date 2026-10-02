# E-commerce frontend

پایهٔ رابط کاربری فروشگاه با Next.js App Router، TypeScript و Tailwind CSS.

## اجرای محلی

به Node.js 24 LTS و npm نیاز است. سپس:

```bash
cp .env.example .env.local
npm install
npm run dev
```

متغیر `DJANGO_API_URL` آدرس داخلی Django برای درخواست‌های سمت سرور است. این
مقدار نباید با پیشوند `NEXT_PUBLIC_` در اختیار مرورگر قرار گیرد.

## بررسی کیفیت

```bash
npm run lint
npm run typecheck
npm run build
```
