import type { Metadata } from "next";
import localFont from "next/font/local";
import type { ReactNode } from "react";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

import "./globals.css";

const vazirmatn = localFont({
  src: "./fonts/Vazirmatn-wght.woff2",
  variable: "--font-vazirmatn",
  display: "swap",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "فروشگاه",
  description: "فروشگاه اینترنتی فارسی",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body className={`${vazirmatn.variable} antialiased`}>
        <a
          href="#main-content"
          className="sr-only z-50 rounded-lg bg-primary px-4 py-3 font-bold text-primary-foreground shadow-card focus:not-sr-only focus:fixed focus:start-4 focus:top-4"
        >
          پرش به محتوای اصلی
        </a>
        <div className="flex min-h-dvh flex-col">
          <SiteHeader />
          <main id="main-content" className="flex-1">
            {children}
          </main>
          <SiteFooter />
        </div>
      </body>
    </html>
  );
}
