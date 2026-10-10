import type { Metadata } from "next";

import { DashboardOverview } from "@/components/dashboard-overview";

export const metadata: Metadata = { title: "داشبورد عملیات | نقش‌جهان", robots: { index: false, follow: false } };

export default function DashboardPage() { return <DashboardOverview />; }
