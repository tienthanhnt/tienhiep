'use client';

import React, { useMemo, useEffect, useRef, useState } from 'react';
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
  chapterCount: number;
}

interface ChapterNavItem {
  id: number;
  chapter_number: number;
  title: string;
}

const RECENT_READING_KEY = 'tang-kinh-cac:recent-reading';
const RECENT_READING_LIMIT = 1;
const TOC_PAGE_SIZE = 100;

export default function ChapterReader({
  bookId,
  bookTitle,
  chapterNumber,
  chapterTitle,
  contentHtml,
  prevNum,
  nextNum,
  chapterCount,
}: ChapterReaderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [fontSize, setFontSize] = useState<number>(19); // Default 19px for super comfortable reading
  const [theme, setTheme] = useState<'parchment' | 'dark' | 'white'>('parchment');
  const [loadingChapter, setLoadingChapter] = useState<number | null>(null);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [showToc, setShowToc] = useState(false);
  const [tocQuery, setTocQuery] = useState('');
  const [tocPage, setTocPage] = useState(() => Math.max(0, Math.floor((chapterNumber - 1) / TOC_PAGE_SIZE)));
  const [tocCache, setTocCache] = useState<Record<number, ChapterNavItem[]>>({});
  const [tocLoading, setTocLoading] = useState(false);
  const [tocError, setTocError] = useState('');
  const [tocSearchResults, setTocSearchResults] = useState<ChapterNavItem[] | null>(null);
  const [tocSearchLoading, setTocSearchLoading] = useState(false);
  const trackedViewKey = useRef('');

  const prevHref = prevNum ? `/books/${bookId}/chapters/${prevNum}` : null;
  const nextHref = nextNum ? `/books/${bookId}/chapters/${nextNum}` : null;
  const totalTocPages = Math.max(1, Math.ceil((chapterCount || chapterNumber) / TOC_PAGE_SIZE));
  const currentTocChapters = useMemo(() => tocCache[tocPage] || [], [tocCache, tocPage]);
  const tocRanges = useMemo(() => {
    return Array.from({ length: totalTocPages }, (_, index) => {
      const first = index * TOC_PAGE_SIZE + 1;
      const last = Math.min((index + 1) * TOC_PAGE_SIZE, chapterCount || first + TOC_PAGE_SIZE - 1);
      return {
        index,
        label: `Chương ${first}-${last}`,
      };
    });
  }, [chapterCount, totalTocPages]);

  const filteredChapters = useMemo(() => {
    const keyword = tocQuery.trim().toLowerCase();
    if (!keyword) return currentTocChapters;
    if (tocSearchResults) return tocSearchResults;
    return currentTocChapters.filter((chapter) => (
      chapter.title.toLowerCase().includes(keyword) ||
      String(chapter.chapter_number).includes(keyword)
    ));
  }, [currentTocChapters, tocQuery, tocSearchResults]);

  useEffect(() => {
    if (prevHref) router.prefetch(prevHref);
    if (nextHref) router.prefetch(nextHref);
  }, [nextHref, prevHref, router]);

  useEffect(() => {
    const viewKey = `${bookId}:${chapterNumber}`;
    if (trackedViewKey.current === viewKey) return;
    trackedViewKey.current = viewKey;

    fetch(`/api/books/${bookId}/views`, {
      method: 'POST',
      keepalive: true,
    }).catch(() => {
      // View tracking should never interrupt reading.
    });
  }, [bookId, chapterNumber]);

  useEffect(() => {
    setLoadingChapter(null);
    setShowToc(false);
    setTocQuery('');
    setTocSearchResults(null);
    setTocPage(Math.max(0, Math.floor((chapterNumber - 1) / TOC_PAGE_SIZE)));
  }, [chapterNumber, pathname]);

  useEffect(() => {
    if (!showToc || tocCache[tocPage]) return;

    const controller = new AbortController();
    const loadTocPage = async () => {
      const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
      const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
      if (!url || !key) {
        setTocError('Thiếu cấu hình Supabase.');
        return;
      }

      setTocLoading(true);
      setTocError('');

      try {
        const from = tocPage * TOC_PAGE_SIZE;
        const to = from + TOC_PAGE_SIZE - 1;
        const response = await fetch(
          `${url}/rest/v1/chapters?book_id=eq.${bookId}&select=id,chapter_number,title&order=chapter_number.asc`,
          {
            headers: {
              apikey: key,
              Authorization: `Bearer ${key}`,
              Range: `${from}-${to}`,
            },
            signal: controller.signal,
          }
        );

        if (!response.ok) throw new Error('Không tải được mục lục.');
        const data = await response.json() as ChapterNavItem[];
        setTocCache((current) => ({ ...current, [tocPage]: data }));
      } catch (error) {
        if (!controller.signal.aborted) {
          setTocError(error instanceof Error ? error.message : 'Không tải được mục lục.');
        }
      } finally {
        if (!controller.signal.aborted) {
          setTocLoading(false);
        }
      }
    };

    loadTocPage();
    return () => controller.abort();
  }, [bookId, showToc, tocCache, tocPage]);

  useEffect(() => {
    const keyword = tocQuery.trim();
    if (!showToc || keyword.length < 2) {
      setTocSearchResults(null);
      setTocSearchLoading(false);
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
      const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
      if (!url || !key) return;

      setTocSearchLoading(true);
      try {
        const escapedKeyword = keyword.replace(/[%*_]/g, '');
        const chapterNumber = Number(escapedKeyword);
        const filters = [`title.ilike.*${encodeURIComponent(escapedKeyword)}*`];
        if (Number.isInteger(chapterNumber)) {
          filters.push(`chapter_number.eq.${chapterNumber}`);
        }

        const response = await fetch(
          `${url}/rest/v1/chapters?book_id=eq.${bookId}&select=id,chapter_number,title&or=(${filters.join(',')})&order=chapter_number.asc&limit=100`,
          {
            headers: {
              apikey: key,
              Authorization: `Bearer ${key}`,
            },
            signal: controller.signal,
          }
        );

        if (!response.ok) throw new Error();
        const data = await response.json() as ChapterNavItem[];
        setTocSearchResults(data);
      } catch {
        if (!controller.signal.aborted) {
          setTocSearchResults([]);
        }
      } finally {
        if (!controller.signal.aborted) {
          setTocSearchLoading(false);
        }
      }
    }, 250);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [bookId, showToc, tocQuery]);

  useEffect(() => {
    window.history.scrollRestoration = 'manual';
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    setScrollProgress(0);

    const frame = window.requestAnimationFrame(() => {
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      setScrollProgress(0);
    });

    return () => window.cancelAnimationFrame(frame);
  }, [chapterNumber]);

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
      ].slice(0, RECENT_READING_LIMIT);
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

  const renderTocButton = () => (
    <button
      type="button"
      onClick={() => setShowToc((current) => !current)}
      className="text-[#A37B34] transition-colors hover:text-[#7A5B1E] hover:underline"
      aria-expanded={showToc}
    >
      Mục Lục
    </button>
  );

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

        {renderTocButton()}

        {renderChapterLink(nextHref, nextNum, 'Chương Sau →', 'Chương Sau →')}
      </div>

      {showToc && (
        <div className="rounded-lg border border-[#D8CDBB] bg-[#FBFAF7]/95 p-4 shadow-[0_10px_28px_rgba(66,52,35,0.08)]">
          <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#2C2825]">Mục lục chương</h2>
              <p className="mt-1 text-xs text-[#8C8373]">{chapterCount || 'Nhiều'} chương</p>
            </div>
            <input
              value={tocQuery}
              onChange={(event) => setTocQuery(event.target.value)}
              placeholder="Tìm chương"
              className="w-full rounded-md border border-[#DDD5C8] bg-white/90 px-3 py-2 text-sm text-[#2C2825] outline-none transition-colors placeholder:text-[#9A9182] focus:border-[#B99654] sm:w-56"
            />
          </div>

          {tocQuery.trim().length === 0 && totalTocPages > 1 && (
            <div className="mb-3 flex flex-col gap-2 rounded-md border border-[#E8E0D2] bg-white/60 p-2.5 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-xs font-semibold text-[#6B6357]">
                {tocRanges[tocPage]?.label}
              </span>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setTocPage((current) => Math.max(0, current - 1))}
                  disabled={tocPage === 0}
                  className="rounded-md border border-[#D0BC90] px-3 py-1.5 text-xs font-semibold text-[#5C5449] transition-colors hover:bg-[#F3EBDD] disabled:cursor-not-allowed disabled:opacity-45"
                >
                  Trước
                </button>
                <select
                  value={tocPage}
                  onChange={(event) => setTocPage(Number(event.target.value))}
                  className="max-w-full rounded-md border border-[#D0BC90] bg-[#FBFAF7] px-3 py-1.5 text-xs font-semibold text-[#5C5449] outline-none focus:border-[#B99654]"
                >
                  {tocRanges.map((range) => (
                    <option key={range.index} value={range.index}>
                      {range.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setTocPage((current) => Math.min(totalTocPages - 1, current + 1))}
                  disabled={tocPage >= totalTocPages - 1}
                  className="rounded-md border border-[#D0BC90] px-3 py-1.5 text-xs font-semibold text-[#5C5449] transition-colors hover:bg-[#F3EBDD] disabled:cursor-not-allowed disabled:opacity-45"
                >
                  Sau
                </button>
              </div>
            </div>
          )}

          <div className="max-h-80 overflow-y-auto pr-1">
            {(tocLoading || tocSearchLoading) ? (
              <p className="py-8 text-center text-sm text-[#8C8373]">
                Đang tải mục lục...
              </p>
            ) : tocError ? (
              <p className="py-8 text-center text-sm text-[#A04A3A]">
                {tocError}
              </p>
            ) : filteredChapters.length === 0 ? (
              <p className="py-8 text-center text-sm text-[#8C8373]">
                Không tìm thấy chương phù hợp.
              </p>
            ) : (
              <>
              {tocQuery.trim().length > 0 && (
                <p className="mb-3 text-xs font-medium text-[#8C8373]">
                  Tìm thấy {filteredChapters.length} chương phù hợp.
                </p>
              )}
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {filteredChapters.map((chapter) => {
                  const isCurrent = chapter.chapter_number === chapterNumber;
                  return (
                    <Link
                      key={chapter.id}
                      href={`/books/${bookId}/chapters/${chapter.chapter_number}`}
                      prefetch={false}
                      onClick={() => setLoadingChapter(chapter.chapter_number)}
                      className={`flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm transition-colors ${
                        isCurrent
                          ? 'border-[#B99654] bg-[#F3EBDD] text-[#7A5B1E]'
                          : 'border-[#E8E0D2] bg-white/82 text-[#2C2825] hover:border-[#D0BC90] hover:bg-[#F4EFE6] hover:text-[#7A5B1E]'
                      }`}
                    >
                      <span className="truncate">{chapter.title}</span>
                      <span className="shrink-0 text-xs text-[#8C8373]">
                        {chapter.chapter_number}
                      </span>
                    </Link>
                  );
                })}
              </div>
              </>
            )}
          </div>
        </div>
      )}

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

        {renderTocButton()}

        {renderChapterLink(nextHref, nextNum, 'Chương Sau →', 'Chương Sau →')}
      </div>
    </div>
  );
}
