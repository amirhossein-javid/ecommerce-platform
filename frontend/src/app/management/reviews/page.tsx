import type { Metadata } from "next";

import { Container } from "@/components/container";
import { ReviewManagementPanel } from "@/components/review-management-panel";

export const metadata: Metadata = {
  title: "مدیریت نظرها | نقش‌جهان",
  description: "پنل مدیریت نظرها و پاسخ رسمی فروشگاه",
  robots: { index: false, follow: false },
};

export default function ReviewManagementPage() {
  return (
    <Container className="py-6 sm:py-10 lg:py-12">
      <header className="mb-6 rounded-[1.5rem] bg-lapis p-6 text-white shadow-card sm:p-8">
        <p className="text-xs font-black text-gold-light">مدیریت فروشگاه</p>
        <h1 className="mt-2 text-2xl font-black sm:text-3xl">نظرها و پاسخ‌های رسمی</h1>
        <p className="mt-3 max-w-2xl text-sm leading-8 text-white/75">بررسی نظر مشتری، تأیید یا رد صریح و مدیریت یک پاسخ رسمی برای هر نظر.</p>
      </header>
      <ReviewManagementPanel />
    </Container>
  );
}
