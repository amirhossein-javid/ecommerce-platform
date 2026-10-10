import type { Metadata } from "next";

import { OrderManagementPanel } from "@/components/order-management-panel";

export const metadata: Metadata = { title: "مدیریت سفارش‌ها | نقش‌جهان", robots: { index: false, follow: false } };

export default function DashboardOrdersPage() { return <OrderManagementPanel />; }
