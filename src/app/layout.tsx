import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tàng Kinh Các - Điện Đọc Truyện Tiên Hiệp",
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
        {/* Sticky Header */}
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
                <span className="text-[10px] text-[#A69C88] tracking-widest uppercase">Tiên Hiệp Thư Viện</span>
              </div>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-8 text-sm font-medium">
              <Link href="/" className="hover:text-[#D4AF37] transition-colors relative py-1 after:absolute after:bottom-0 after:left-0 after:w-0 after:h-[2px] after:bg-[#D4AF37] hover:after:w-full after:transition-all">
                Trang Chủ
              </Link>
              <Link href="/" className="hover:text-[#D4AF37] transition-colors relative py-1 after:absolute after:bottom-0 after:left-0 after:w-0 after:h-[2px] after:bg-[#D4AF37] hover:after:w-full after:transition-all">
                Mới Cập Nhật
              </Link>
              <Link href="/" className="hover:text-[#D4AF37] transition-colors relative py-1 after:absolute after:bottom-0 after:left-0 after:w-0 after:h-[2px] after:bg-[#D4AF37] hover:after:w-full after:transition-all">
                Danh Sách Truyện
              </Link>
            </nav>

            {/* Right Action */}
            <div className="flex items-center gap-3">
              <span className="text-xs bg-[#242A38] border border-[#C69C4E]/20 text-[#C69C4E] px-3 py-1.5 rounded-full">
                📜 Đọc Sách
              </span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-6xl mx-auto px-4 py-8 flex-1 w-full">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-[#13161F] text-[#8C8275] border-t border-[#C69C4E]/20 py-10 mt-16 text-sm">
          <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4 text-center md:text-left">
            <div>
              <p className="font-semibold text-[#D4AF37] text-base mb-1">Tàng Kinh Các — Kho Tàng Tiên Hiệp Kỳ Ảo</p>
              <p className="text-xs text-[#6B6357]">Không gian đọc truyện thư thái, trải nghiệm chữ mượt mà chuẩn văn phong.</p>
            </div>
            <div className="text-xs text-[#6B6357]">
              &copy; 2026 Tàng Kinh Các. Bảo lưu mọi quyền.
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
