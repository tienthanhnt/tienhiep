import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tàng Kinh Các - Đọc Truyện Tiên Hiệp",
  description: "Trang đọc truyện tiên hiệp, huyền huyễn chất lượng cao với văn phong thuần Việt.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="min-h-screen flex flex-col antialiased">
        {/* Header */}
        <header className="bg-[#181D27] text-[#E5DDCB] border-b border-[#C69C4E]/30 sticky top-0 z-50 shadow-md">
          <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
            
            {/* Logo */}
            <Link href="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#C69C4E] to-[#8C6D2D] p-[1px] flex items-center justify-center shadow-inner">
                <div className="w-full h-full bg-[#181D27] rounded-full flex items-center justify-center text-[#D4AF37] font-bold text-lg group-hover:bg-[#C69C4E] group-hover:text-[#181D27] transition-all">
                  ☯
                </div>
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-lg tracking-wider gold-gradient-text">TÀNG KINH CÁC</span>
                <span className="text-[10px] text-[#A69C88] tracking-widest uppercase">Thư Viện Truyện</span>
              </div>
            </Link>

            {/* Navigation */}
            <nav className="flex items-center gap-6 text-sm font-medium">
              <Link href="/" className="text-[#D4AF37] hover:underline transition-colors py-1">
                Trang Chủ
              </Link>
            </nav>

          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-6xl mx-auto px-4 py-6 flex-1 w-full">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-[#13161F] text-[#8C8275] border-t border-[#C69C4E]/20 py-6 mt-12 text-sm">
          <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left text-xs">
            <div>
              <span className="font-semibold text-[#D4AF37]">Tàng Kinh Các</span> — Nền tảng đọc truyện tối giản, mượt mà.
            </div>
            <div className="text-[#6B6357]">
              &copy; 2026 Tàng Kinh Các.
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
