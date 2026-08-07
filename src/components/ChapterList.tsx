'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

interface Chapter {
  id: number;
  chapter_number: number;
  title: string;
  created_at: string;
}

interface ChapterListProps {
  bookId: number;
  chapters: Chapter[];
}

export default function ChapterList({ bookId, chapters }: ChapterListProps) {
  const [query, setQuery] = useState('');

  const latestChapter = chapters[chapters.length - 1];
  const filteredChapters = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return chapters;

    return chapters.filter((chapter) => {
      return (
        chapter.title.toLowerCase().includes(keyword) ||
        String(chapter.chapter_number).includes(keyword)
      );
    });
  }, [chapters, query]);

  return (
    <div className="p-5 md:p-6 rounded-lg border border-[#DDD5C8] bg-[#FBFAF7]/90 shadow-[0_8px_26px_rgba(66,52,35,0.05)]">
      <div className="mb-5 flex flex-col gap-3 border-b border-[#DDD5C8] pb-4 md:flex-row md:items-center md:justify-between">
        <h2 className="text-lg font-bold text-[#2C2825]">
          Danh sách chương ({chapters.length})
        </h2>

        {latestChapter && (
          <Link
            href={`/books/${bookId}/chapters/${latestChapter.chapter_number}`}
            className="inline-flex w-fit items-center justify-center rounded-md border border-[#D0BC90] bg-[#F3EBDD] px-3.5 py-2 text-xs font-semibold text-[#5C5449] transition-colors hover:bg-[#C69C4E] hover:text-white"
          >
            Đọc chương mới nhất
          </Link>
        )}
      </div>

      {chapters.length === 0 ? (
        <p className="text-[#8C8373] py-6 text-center text-sm">Chưa có chương nào được upload.</p>
      ) : (
        <>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm tên hoặc số chương"
            className="mb-4 w-full rounded-md border border-[#DDD5C8] bg-white/80 px-3 py-2.5 text-sm text-[#2C2825] outline-none transition-colors placeholder:text-[#9A9182] focus:border-[#B99654]"
          />

          {filteredChapters.length === 0 ? (
            <p className="py-8 text-center text-sm text-[#8C8373]">
              Không tìm thấy chương phù hợp.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {filteredChapters.map((ch) => (
                <Link
                  key={ch.id}
                  href={`/books/${bookId}/chapters/${ch.chapter_number}`}
                  className="p-3 rounded-md bg-white/78 hover:bg-[#F4EFE6] text-[#2C2825] hover:text-[#7A5B1E] text-sm font-medium transition-all flex justify-between items-center border border-[#E8E0D2] hover:border-[#D0BC90]"
                >
                  <span className="truncate">{ch.title}</span>
                  <span className="text-xs text-[#8C8373] shrink-0 ml-3">
                    Chương {ch.chapter_number}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
