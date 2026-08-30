import type { Metadata } from "next";
import Link from "next/link";
import AdsterraSocialBar from "@/components/AdsterraSocialBar";
import { getSiteUrl, SITE_NAME } from "@/lib/seo";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(getSiteUrl()),
  title: {
    default: SITE_NAME,
    template: `%s | ${SITE_NAME}`,
  },
  description: "Đọc truyện tiên hiệp, huyền huyễn, kiếm hiệp và tu tiên dịch full tiếng Việt miễn phí, cập nhật chương mới mỗi ngày.",
  keywords: [
    "đọc truyện tiên hiệp",
    "truyện tiên hiệp",
    "truyện huyền huyễn",
    "truyện kiếm hiệp",
    "truyện tu tiên",
    "truyện full",
    "Tiên Hiệp Lâu",
  ],
  applicationName: SITE_NAME,
  alternates: {
    canonical: "/",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: "Đọc truyện tiên hiệp, huyền huyễn, kiếm hiệp và tu tiên dịch full tiếng Việt miễn phí, cập nhật chương mới mỗi ngày.",
    url: "/",
    locale: "vi_VN",
  },
  twitter: {
    card: "summary",
    title: SITE_NAME,
    description: "Đọc truyện tiên hiệp, huyền huyễn, kiếm hiệp và tu tiên dịch full tiếng Việt miễn phí, cập nhật chương mới mỗi ngày.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="min-h-screen flex flex-col antialiased">

        <header className="sticky top-0 z-50 border-b border-[#DDD5C8]/80 bg-[#FBFAF7]/90 shadow-[0_1px_12px_rgba(66,52,35,0.04)] backdrop-blur-md">
          <div className="max-w-6xl mx-auto px-5 h-14 flex items-center justify-between">
            <Link href="/" className="group flex items-center gap-2.5 shrink-0 text-[#29241E]">
              <span className="flex h-8 w-8 items-center justify-center rounded-full border border-[#2C2825]/25 bg-white/65 text-[#111111] text-lg leading-none shadow-inner transition-colors group-hover:border-[#111111]/55 group-hover:bg-white/90">
                ☯
              </span>
              <span className="font-bold text-base tracking-wide group-hover:text-[#7A5B1E] transition-colors">Tiên Hiệp Lâu</span>
            </Link>

            <nav className="flex items-center gap-6 text-sm">
              <Link href="/" className="text-[#665E53] hover:text-[#2C2825] transition-colors py-1 text-sm font-medium">
                Trang Chủ
              </Link>
            </nav>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-5 py-7 flex-1 w-full">
          {children}
        </main>

        <footer className="border-t border-[#DDD5C8]/80 py-6 mt-12 text-[#7A7365]">
          <div className="max-w-6xl mx-auto px-5 flex items-center justify-between gap-4 text-xs">
            <p>Tiên Hiệp Lâu</p>
            <p>&copy; 2026</p>
          </div>
        </footer>

        <AdsterraSocialBar />
      </body>
    </html>
  );
}
