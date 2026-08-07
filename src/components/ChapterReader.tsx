'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

interface ChapterReaderProps {
  bookId: number;
  bookTitle: string;
  chapterNumber: number;
  chapterTitle: string;
  contentHtml: string;
  prevNum: number | null;
  nextNum: number | null;
}

const RECENT_READING_KEY = 'tang-kinh-cac:recent-reading';

export default function ChapterReader({
  bookId,
  bookTitle,
  chapterNumber,
  chapterTitle,
  contentHtml,
  prevNum,
  nextNum,
}: ChapterReaderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [fontSize, setFontSize] = useState<number>(19); // Default 19px for super comfortable reading
  const [theme, setTheme] = useState<'parchment' | 'dark' | 'white'>('parchment');
  const [loadingChapter, setLoadingChapter] = useState<number | null>(null);
  const [scrollProgress, setScrollProgress] = useState(0);

  const prevHref = prevNum ? `/books/${bookId}/chapters/${prevNum}` : null;
  const nextHref = nextNum ? `/books/${bookId}/chapters/${nextNum}` : null;

  useEffect(() => {
    if (prevHref) router.prefetch(prevHref);
    if (nextHref) router.prefetch(nextHref);
  }, [nextHref, prevHref, router]);

  useEffect(() => {
    setLoadingChapter(null);
  }, [pathname]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(RECENT_READING_KEY);
      const current = raw ? JSON.parse(raw) : [];
      const list = Array.isArray(current) ? current : [];
      const next = [
        {
          bookId,
          bookTitle,
          chapterNumber,
          chapterTitle,
          updatedAt: Date.now(),
        },
        ...list.filter((item) => item?.bookId !== bookId),
      ].slice(0, 6);
      window.localStorage.setItem(RECENT_READING_KEY, JSON.stringify(next));
    } catch {
      // Ignore private browsing or malformed localStorage data.
    }
  }, [bookId, bookTitle, chapterNumber, chapterTitle]);

  useEffect(() => {
    const updateProgress = () => {
      const scrollTop = window.scrollY;
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      setScrollProgress(maxScroll > 0 ? Math.min(100, Math.max(0, (scrollTop / maxScroll) * 100)) : 0);
    };

    updateProgress();
    window.addEventListener('scroll', updateProgress, { passive: true });
    window.addEventListener('resize', updateProgress);

    return () => {
      window.removeEventListener('scroll', updateProgress);
      window.removeEventListener('resize', updateProgress);
    };
  }, [pathname]);

  const getThemeClass = () => {
    switch (theme) {
      case 'dark':
        return 'bg-[#181D27] text-[#D8D2C5] border-[#2C3446] shadow-[0_10px_28px_rgba(10,12,18,0.22)]';
      case 'white':
        return 'bg-white text-[#1A1A1A] border-gray-200 shadow-[0_10px_26px_rgba(66,52,35,0.06)]';
      default:
        return 'bg-[#F7F0E4] text-[#2C2825] border-[#D5BD8C] shadow-[0_10px_30px_rgba(66,52,35,0.08)]';
    }
  };

  const renderChapterLink = (
    href: string | null,
    targetChapter: number | null,
    label: string,
    disabledLabel: string
  ) => {
    if (!href || !targetChapter) {
      return (
        <span className="px-4 py-2 rounded-lg bg-gray-200 text-gray-400 cursor-not-allowed min-w-[118px] text-center">
          {disabledLabel}
        </span>
      );
    }

    const isLoading = loadingChapter === targetChapter;

    return (
      <Link
        href={href}
        prefetch
        onMouseEnter={() => router.prefetch(href)}
        onTouchStart={() => router.prefetch(href)}
        onClick={() => setLoadingChapter(targetChapter)}
        aria-busy={isLoading}
        className={`px-4 py-2 rounded-md text-[#5C5449] transition-all border border-[#C69C4E]/25 min-w-[118px] text-center shadow-sm ${
          isLoading
            ? 'bg-[#C69C4E] text-white cursor-wait shadow-sm'
            : 'bg-[#F3EBDD] hover:bg-[#C69C4E] hover:text-white hover:shadow-md'
        }`}
      >
        {isLoading ? 'Đang tải...' : label}
      </Link>
    );
  };

  const scrollToPageEdge = (position: 'top' | 'bottom') => {
    window.scrollTo({
      top: position === 'top' ? 0 : document.documentElement.scrollHeight,
      behavior: 'smooth',
    });
  };

  return (
    <div className="max-w-3xl mx-auto py-4 flex flex-col gap-6">
      <div className="fixed left-0 right-0 top-0 z-[55] h-0.5 bg-transparent">
        <div
          className="h-full bg-[#B99654] transition-[width] duration-150"
          style={{ width: `${scrollProgress}%` }}
        />
      </div>

      {loadingChapter !== null && (
        <div className="fixed left-0 right-0 top-0 z-[60] h-1 bg-[#E8E0D2]">
          <div className="h-full w-1/2 animate-pulse bg-[#C69C4E]" />
        </div>
      )}

      <div className="fixed bottom-5 right-4 z-40 hidden flex-col gap-2 md:flex">
        <button
          type="button"
          onClick={() => scrollToPageEdge('top')}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-[#D8CDBB] bg-[#FBFAF7]/90 text-sm font-bold text-[#7A5B1E] shadow-md backdrop-blur transition-colors hover:bg-[#F3EBDD]"
          title="Lên đầu chương"
        >
          ↑
        </button>
        <button
          type="button"
          onClick={() => scrollToPageEdge('bottom')}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-[#D8CDBB] bg-[#FBFAF7]/90 text-sm font-bold text-[#7A5B1E] shadow-md backdrop-blur transition-colors hover:bg-[#F3EBDD]"
          title="Xuống cuối chương"
        >
          ↓
        </button>
      </div>

      {/* Top Header Navigation */}
      <div className="flex flex-wrap justify-between items-center text-xs text-[#7A7365] border-b border-[#C69C4E]/20 pb-3 gap-2">
        <Link href={`/books/${bookId}`} className="hover:text-[#A37B34] font-medium flex items-center gap-1">
          &larr; {bookTitle}
        </Link>
        <span className="font-semibold text-[#2C2825] bg-[#E8E0D2] px-3 py-1 rounded-full shadow-sm">
          Chương {chapterNumber}
        </span>
      </div>

      {/* Chapter Reader Controls Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-[#211D19] text-[#EDE5D6] shadow-[0_8px_22px_rgba(33,29,25,0.16)] border border-[#C69C4E]/25 text-xs">
        {/* Font Size Adjuster */}
        <div className="flex items-center gap-2">
          <span className="text-[#A69C88]">Cỡ chữ:</span>
          <button
            onClick={() => setFontSize((prev) => Math.max(15, prev - 2))}
            className="w-7 h-7 rounded bg-[#342E27] hover:bg-[#C69C4E] hover:text-[#181D27] font-bold transition-all"
            title="Giảm cỡ chữ"
          >
            A-
          </button>
          <span className="font-bold text-[#D8B45F] w-6 text-center">{fontSize}</span>
          <button
            onClick={() => setFontSize((prev) => Math.min(28, prev + 2))}
            className="w-7 h-7 rounded bg-[#342E27] hover:bg-[#C69C4E] hover:text-[#181D27] font-bold transition-all"
            title="Tăng cỡ chữ"
          >
            A+
          </button>
        </div>

        {/* Theme Picker */}
        <div className="flex items-center gap-2">
          <span className="text-[#A69C88]">Nền:</span>
          <button
            onClick={() => setTheme('parchment')}
            className={`px-2.5 py-1 rounded border text-[11px] font-medium transition-all ${
              theme === 'parchment' ? 'bg-[#F4EFE6] text-[#2C2825] border-[#C69C4E]' : 'bg-[#342E27] text-[#B8AE9C] border-transparent'
            }`}
          >
            Giấy Cổ
          </button>
          <button
            onClick={() => setTheme('white')}
            className={`px-2.5 py-1 rounded border text-[11px] font-medium transition-all ${
              theme === 'white' ? 'bg-white text-black border-white' : 'bg-[#342E27] text-[#B8AE9C] border-transparent'
            }`}
          >
            Sáng
          </button>
          <button
            onClick={() => setTheme('dark')}
            className={`px-2.5 py-1 rounded border text-[11px] font-medium transition-all ${
              theme === 'dark' ? 'bg-[#181D27] text-[#D4AF37] border-[#D4AF37]' : 'bg-[#342E27] text-[#B8AE9C] border-transparent'
            }`}
          >
            Đêm
          </button>
        </div>
      </div>

      {/* Navigation Buttons Top */}
      <div className="flex justify-between items-center text-xs font-semibold">
        {renderChapterLink(prevHref, prevNum, '← Chương Trước', '← Chương Trước')}

        <Link href={`/books/${bookId}`} className="text-[#A37B34] hover:underline">
          Mục Lục
        </Link>

        {renderChapterLink(nextHref, nextNum, 'Chương Sau →', 'Chương Sau →')}
      </div>

      {/* Main Chapter Title & Reading Content */}
      <div className={`p-6 md:p-12 rounded-lg border transition-all duration-300 ${getThemeClass()}`}>
        <h1 className="text-2xl md:text-3xl font-bold text-center mb-8 pb-4 border-b border-current/15 leading-snug font-serif-reading">
          {chapterTitle}
        </h1>

        <div
          className="reading-prose font-serif-reading leading-relaxed whitespace-pre-wrap tracking-normal"
          style={{ fontSize: `${fontSize}px`, lineHeight: '1.85' }}
          dangerouslySetInnerHTML={{ __html: contentHtml }}
        />
      </div>

      {/* Navigation Buttons Bottom */}
      <div className="flex justify-between items-center text-xs font-semibold mt-4">
        {renderChapterLink(prevHref, prevNum, '← Chương Trước', '← Chương Trước')}

        <Link href={`/books/${bookId}`} className="text-[#A37B34] hover:underline">
          Mục Lục
        </Link>

        {renderChapterLink(nextHref, nextNum, 'Chương Sau →', 'Chương Sau →')}
      </div>
    </div>
  );
}
