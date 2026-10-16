import type { Metadata } from "next";

import { ReviewManagementPanel } from "@/components/review-management-panel";

export const metadata: Metadata = { title: "مدیریت نظرها | نقش‌جهان", description: "پنل مدیریت نظرها و پاسخ رسمی فروشگاه", robots: { index: false, follow: false } };

export default function DashboardReviewsPage() { return <ReviewManagementPanel />; }
