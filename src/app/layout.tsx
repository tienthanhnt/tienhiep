import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tàng Kinh Các — Bồng Lai Tiên Cảnh",
  description: "Thư viện truyện tiên hiệp chất lượng cao, văn phong thuần Việt, cổ phong đền đài.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="min-h-screen flex flex-col antialiased">

        {/* ══════════════ HEADER — Đình đài Bồng Lai ══════════════ */}
        <header className="bg-[#0F1520]/90 backdrop-blur-md text-[#E8DFC8] sticky top-0 z-50 border-b border-[#C69C4E]/30">
          {/* Top ornamental stripe */}
          <div className="h-0.5 bg-gradient-to-r from-transparent via-[#C69C4E]/70 to-transparent" />

          <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between">

            {/* Logo */}
            <Link href="/" className="flex items-center gap-3 group shrink-0">
              <div className="relative w-10 h-10 flex items-center justify-center">
                {/* Outer ring */}
                <div className="absolute inset-0 rounded-full border border-[#C69C4E]/50 group-hover:border-[#C69C4E] transition-colors" />
                {/* Inner glow */}
                <div className="absolute inset-1 rounded-full bg-gradient-to-br from-[#C69C4E]/20 to-transparent" />
                <span className="text-[#D4AF37] text-xl z-10">☯</span>
              </div>
              <div className="flex flex-col leading-tight">
                <span className="font-bold tracking-[0.15em] text-base gold-gradient-text">TÀNG KINH CÁC</span>
                <span className="text-[9px] text-[#8A816E] tracking-[0.3em] uppercase">Bồng Lai Tiên Cảnh</span>
              </div>
            </Link>

            {/* Navigations */}
            <nav className="flex items-center gap-6 text-sm">
              <Link href="/" className="text-[#C8BC9E] hover:text-[#D4AF37] transition-colors py-1 text-xs tracking-wide">
                Trang Chủ
              </Link>
            </nav>

          </div>

          {/* Bottom ornamental stripe */}
          <div className="h-px bg-gradient-to-r from-transparent via-[#C69C4E]/30 to-transparent" />
        </header>

        {/* ══════════════ MAIN ══════════════ */}
        <main className="max-w-6xl mx-auto px-5 py-8 flex-1 w-full">
          {children}
        </main>

        {/* ══════════════ FOOTER ══════════════ */}
        <footer className="bg-[#0B1018]/95 text-[#6E6558] border-t border-[#C69C4E]/20 py-8 mt-16">
          <div className="max-w-6xl mx-auto px-5 flex flex-col items-center gap-3 text-center">
            <div className="h-px w-32 bg-gradient-to-r from-transparent via-[#C69C4E]/50 to-transparent" />
            <p className="text-sm font-cinzel text-[#C69C4E]/70 tracking-widest">TÀNG KINH CÁC</p>
            <p className="text-xs text-[#4E4840]">Kho tàng tiên hiệp — đọc chữ như uống trà, tâm thần tự thái.</p>
            <p className="text-xs text-[#3A352E]">&copy; 2026 Tàng Kinh Các.</p>
          </div>
        </footer>

      </body>
    </html>
  );
}
