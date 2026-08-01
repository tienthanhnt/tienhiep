import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export const metadata: Metadata = {
  title: "Website Đọc Truyện Tiên Hiệp",
  description: "Trang đọc truyện tiên hiệp online miễn phí.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className={inter.className}>
        <header className="bg-white shadow-sm sticky top-0 z-50">
          <div className="container mx-auto px-4 h-14 flex items-center justify-between">
            <div className="text-xl font-bold text-blue-600">TiênHiệp.net</div>
            <nav className="hidden md:flex gap-6 text-sm font-medium">
              <a href="#" className="hover:text-blue-600 transition-colors">Trang chủ</a>
              <a href="#" className="hover:text-blue-600 transition-colors">Mới cập nhật</a>
              <a href="#" className="hover:text-blue-600 transition-colors">Hoàn thành</a>
            </nav>
            <div className="flex items-center gap-4 text-sm font-medium">
              <button className="text-gray-500 hover:text-blue-600">Tìm kiếm</button>
            </div>
          </div>
        </header>
        <main className="container mx-auto px-4 py-8">
          {children}
        </main>
        <footer className="bg-gray-800 text-white py-8 mt-12">
          <div className="container mx-auto px-4 text-center text-sm text-gray-400">
            &copy; 2026 TiênHiệp.net. Đọc truyện online miễn phí.
          </div>
        </footer>
      </body>
    </html>
  );
}
