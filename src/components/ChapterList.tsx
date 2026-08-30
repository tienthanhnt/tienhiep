'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { getChapterPath } from '@/lib/seo';

interface Chapter {
  id: number;
  chapter_number: number;
  title: string;
  created_at: string;
}

interface ChapterListProps {
  bookId: number;
  bookTitle: string;
  initialChapters: Chapter[];
  chapterCount: number;
  initialPage?: number;
}

const CHAPTERS_PER_PAGE = 100;
const CHAPTER_PAGE_PARAM = 'chaptersPage';

function updateChapterPageUrl(nextPage: number) {
  const url = new URL(window.location.href);

  if (nextPage > 0) {
    url.searchParams.set(CHAPTER_PAGE_PARAM, String(nextPage));
  } else {
    url.searchParams.delete(CHAPTER_PAGE_PARAM);
  }

  window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
}

export default function ChapterList({ bookId, bookTitle, initialChapters, chapterCount, initialPage = 0 }: ChapterListProps) {
  const latestChapterNumber = chapterCount || initialChapters[initialChapters.length - 1]?.chapter_number || 1;
  const totalPages = Math.max(1, Math.ceil((chapterCount || initialChapters.length) / CHAPTERS_PER_PAGE));
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(() => Math.min(Math.max(0, initialPage), totalPages - 1));
  const [chapterCache, setChapterCache] = useState<Record<number, Chapter[]>>({ 0: initialChapters });
  const [searchResults, setSearchResults] = useState<Chapter[] | null>(null);
  const [loading, setLoading] = useState(false);

  const currentChapters = useMemo(() => chapterCache[page] || [], [chapterCache, page]);

  const pageRanges = useMemo(() => {
    return Array.from({ length: totalPages }, (_, index) => {
      const firstChapter = index * CHAPTERS_PER_PAGE + 1;
      const lastChapter = Math.min((index + 1) * CHAPTERS_PER_PAGE, chapterCount || firstChapter + CHAPTERS_PER_PAGE - 1);

      return {
        index,
        label: `Chương ${firstChapter}-${lastChapter}`,
      };
    });
  }, [chapterCount, totalPages]);

  useEffect(() => {
    if (chapterCache[page]) return;

    let ignore = false;
    async function loadPage() {
      setLoading(true);
      try {
        const response = await fetch(`/api/books/${bookId}/chapters?page=${page}`);
        const data = await response.json() as { chapters?: Chapter[] };
        if (!ignore) {
          setChapterCache((current) => ({ ...current, [page]: data.chapters || [] }));
        }
      } catch {
        if (!ignore) {
          setChapterCache((current) => ({ ...current, [page]: [] }));
        }
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    loadPage();
    return () => {
      ignore = true;
    };
  }, [bookId, chapterCache, page]);

  useEffect(() => {
    if (!query.trim()) {
      updateChapterPageUrl(page);
    }
  }, [page, query]);

  useEffect(() => {
    const keyword = query.trim();
    if (keyword.length < 2) {
      setSearchResults(null);
      return;
    }

    let ignore = false;
    const timeout = window.setTimeout(async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/books/${bookId}/chapters?q=${encodeURIComponent(keyword)}`);
        const data = await response.json() as { chapters?: Chapter[] };
        if (!ignore) setSearchResults(data.chapters || []);
      } catch {
        if (!ignore) setSearchResults([]);
      } finally {
        if (!ignore) setLoading(false);
      }
    }, 300);

    return () => {
      ignore = true;
      window.clearTimeout(timeout);
    };
  }, [bookId, query]);

  const filteredChapters = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) {
      return currentChapters;
    }

    if (searchResults) return searchResults;

    return currentChapters.filter((chapter) => {
      return (
        chapter.title.toLowerCase().includes(keyword) ||
        String(chapter.chapter_number).includes(keyword)
      );
    });
  }, [currentChapters, query, searchResults]);

  const hasQuery = query.trim().length > 0;

  return (
    <div className="p-5 md:p-6 rounded-lg border border-[#DDD5C8] bg-[#FBFAF7]/90 shadow-[0_8px_26px_rgba(66,52,35,0.05)]">
      <div className="mb-5 flex flex-col gap-3 border-b border-[#DDD5C8] pb-4 md:flex-row md:items-center md:justify-between">
        <h2 className="text-lg font-bold text-[#2C2825]">
          Danh sách chương ({chapterCount || initialChapters.length})
        </h2>

        {latestChapterNumber > 0 && (
          <Link
            href={getChapterPath({ id: bookId, title: bookTitle }, latestChapterNumber)}
            className="inline-flex w-fit items-center justify-center rounded-md border border-[#D0BC90] bg-[#F3EBDD] px-3.5 py-2 text-xs font-semibold text-[#5C5449] transition-colors hover:bg-[#C69C4E] hover:text-white"
          >
            Đọc chương mới nhất
          </Link>
        )}
      </div>

      {(chapterCount || initialChapters.length) === 0 ? (
        <p className="text-[#8C8373] py-6 text-center text-sm">Chưa có chương nào được upload.</p>
      ) : (
        <>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm tên hoặc số chương"
            className="mb-4 w-full rounded-md border border-[#DDD5C8] bg-white/80 px-3 py-2.5 text-sm text-[#2C2825] outline-none transition-colors placeholder:text-[#9A9182] focus:border-[#B99654]"
          />

          {!hasQuery && totalPages > 1 && (
            <div className="mb-4 flex flex-col gap-3 rounded-md border border-[#E8E0D2] bg-white/60 p-3 md:flex-row md:items-center md:justify-between">
              <div className="text-xs font-semibold text-[#6B6357]">
                Đang xem {pageRanges[page]?.label}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                  disabled={page === 0}
                  className="rounded-md border border-[#D0BC90] px-3 py-1.5 text-xs font-semibold text-[#5C5449] transition-colors hover:bg-[#F3EBDD] disabled:cursor-not-allowed disabled:opacity-45"
                >
                  Trước
                </button>

                <select
                  value={page}
                  onChange={(event) => setPage(Number(event.target.value))}
                  className="max-w-full rounded-md border border-[#D0BC90] bg-[#FBFAF7] px-3 py-1.5 text-xs font-semibold text-[#5C5449] outline-none focus:border-[#B99654]"
                >
                  {pageRanges.map((range) => (
                    <option key={range.index} value={range.index}>
                      {range.label}
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
                  disabled={page >= totalPages - 1}
                  className="rounded-md border border-[#D0BC90] px-3 py-1.5 text-xs font-semibold text-[#5C5449] transition-colors hover:bg-[#F3EBDD] disabled:cursor-not-allowed disabled:opacity-45"
                >
                  Sau
                </button>
              </div>
            </div>
          )}

          {loading && filteredChapters.length === 0 ? (
            <p className="py-8 text-center text-sm text-[#8C8373]">
              Đang tải danh sách chương...
            </p>
          ) : filteredChapters.length === 0 ? (
            <p className="py-8 text-center text-sm text-[#8C8373]">
              Không tìm thấy chương phù hợp.
            </p>
          ) : (
            <>
              {hasQuery && (
                <p className="mb-3 text-xs font-medium text-[#8C8373]">
                  Tìm thấy {filteredChapters.length} chương phù hợp.
                </p>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {filteredChapters.map((ch) => (
                  <Link
                    key={ch.id}
                    href={getChapterPath({ id: bookId, title: bookTitle }, ch.chapter_number)}
                    className="p-3 rounded-md bg-white/78 hover:bg-[#F4EFE6] text-[#2C2825] hover:text-[#7A5B1E] text-sm font-medium transition-all flex justify-between items-center border border-[#E8E0D2] hover:border-[#D0BC90]"
                  >
                    <span className="truncate">{ch.title}</span>
                    <span className="text-xs text-[#8C8373] shrink-0 ml-3">
                      Chương {ch.chapter_number}
                    </span>
                  </Link>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
