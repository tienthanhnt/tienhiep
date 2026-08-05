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

  const prevHref = prevNum ? `/books/${bookId}/chapters/${prevNum}` : null;
  const nextHref = nextNum ? `/books/${bookId}/chapters/${nextNum}` : null;

  useEffect(() => {
    if (prevHref) router.prefetch(prevHref);
    if (nextHref) router.prefetch(nextHref);
  }, [nextHref, prevHref, router]);

  useEffect(() => {
    setLoadingChapter(null);
  }, [pathname]);

  const getThemeClass = () => {
    switch (theme) {
      case 'dark':
        return 'bg-[#181D27] text-[#D8D2C5] border-[#2C3446]';
      case 'white':
        return 'bg-white text-[#1A1A1A] border-gray-200';
      default:
        return 'bg-[#F4EFE6] text-[#2C2825] border-[#C69C4E]/30';
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
        className={`px-4 py-2 rounded-lg text-[#5C5449] transition-all border border-[#C69C4E]/20 min-w-[118px] text-center ${
          isLoading
            ? 'bg-[#C69C4E] text-white cursor-wait shadow-sm'
            : 'bg-[#EFE9DC] hover:bg-[#C69C4E] hover:text-white'
        }`}
      >
        {isLoading ? 'Đang tải...' : label}
      </Link>
    );
  };

  return (
    <div className="max-w-3xl mx-auto py-4 flex flex-col gap-6">
      {loadingChapter !== null && (
        <div className="fixed left-0 right-0 top-0 z-[60] h-1 bg-[#E8E0D2]">
          <div className="h-full w-1/2 animate-pulse bg-[#C69C4E]" />
        </div>
      )}

      {/* Top Header Navigation */}
      <div className="flex flex-wrap justify-between items-center text-xs text-[#7A7365] border-b border-[#C69C4E]/20 pb-3 gap-2">
        <Link href={`/books/${bookId}`} className="hover:text-[#A37B34] font-medium flex items-center gap-1">
          &larr; {bookTitle}
        </Link>
        <span className="font-semibold text-[#2C2825] bg-[#E8E0D2] px-3 py-1 rounded-full">
          Chương {chapterNumber}
        </span>
      </div>

      {/* Chapter Reader Controls Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-[#181D27] text-[#E5DDCB] shadow-md border border-[#C69C4E]/30 text-xs">
        {/* Font Size Adjuster */}
        <div className="flex items-center gap-2">
          <span className="text-[#A69C88]">Cỡ chữ:</span>
          <button
            onClick={() => setFontSize((prev) => Math.max(15, prev - 2))}
            className="w-7 h-7 rounded bg-[#242A38] hover:bg-[#C69C4E] hover:text-[#181D27] font-bold transition-all"
            title="Giảm cỡ chữ"
          >
            A-
          </button>
          <span className="font-bold text-[#D4AF37] w-6 text-center">{fontSize}</span>
          <button
            onClick={() => setFontSize((prev) => Math.min(28, prev + 2))}
            className="w-7 h-7 rounded bg-[#242A38] hover:bg-[#C69C4E] hover:text-[#181D27] font-bold transition-all"
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
              theme === 'parchment' ? 'bg-[#F4EFE6] text-[#2C2825] border-[#C69C4E]' : 'bg-[#242A38] text-[#B8AE9C] border-transparent'
            }`}
          >
            Giấy Cổ
          </button>
          <button
            onClick={() => setTheme('white')}
            className={`px-2.5 py-1 rounded border text-[11px] font-medium transition-all ${
              theme === 'white' ? 'bg-white text-black border-white' : 'bg-[#242A38] text-[#B8AE9C] border-transparent'
            }`}
          >
            Sáng
          </button>
          <button
            onClick={() => setTheme('dark')}
            className={`px-2.5 py-1 rounded border text-[11px] font-medium transition-all ${
              theme === 'dark' ? 'bg-[#181D27] text-[#D4AF37] border-[#D4AF37]' : 'bg-[#242A38] text-[#B8AE9C] border-transparent'
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
          📚 Mục Lục
        </Link>

        {renderChapterLink(nextHref, nextNum, 'Chương Sau →', 'Chương Sau →')}
      </div>

      {/* Main Chapter Title & Reading Content */}
      <div className={`p-6 md:p-12 rounded-2xl border shadow-sm transition-all duration-300 ${getThemeClass()}`}>
        <h1 className="text-2xl md:text-3xl font-bold text-center mb-8 pb-4 border-b border-current/15 leading-snug font-serif-reading">
          {chapterTitle}
        </h1>

        <div
          className="font-serif-reading leading-relaxed space-y-4 whitespace-pre-wrap tracking-normal"
          style={{ fontSize: `${fontSize}px`, lineHeight: '1.85' }}
          dangerouslySetInnerHTML={{ __html: contentHtml }}
        />
      </div>

      {/* Navigation Buttons Bottom */}
      <div className="flex justify-between items-center text-xs font-semibold mt-4">
        {renderChapterLink(prevHref, prevNum, '← Chương Trước', '← Chương Trước')}

        <Link href={`/books/${bookId}`} className="text-[#A37B34] hover:underline">
          📚 Mục Lục
        </Link>

        {renderChapterLink(nextHref, nextNum, 'Chương Sau →', 'Chương Sau →')}
      </div>
    </div>
  );
}
