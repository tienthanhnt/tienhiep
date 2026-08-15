'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

interface RecentItem {
  bookId: number;
  bookTitle: string;
  chapterNumber: number;
  chapterTitle: string;
  updatedAt: number;
}

const STORAGE_KEY = 'tang-kinh-cac:recent-reading';
const RECENT_READING_LIMIT = 2;

export default function RecentReading() {
  const [items, setItems] = useState<RecentItem[]>([]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as RecentItem[];
      if (Array.isArray(parsed)) {
        const recentItems = parsed.slice(0, RECENT_READING_LIMIT);
        setItems(recentItems);
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(recentItems));
      }
    } catch {
      setItems([]);
    }
  }, []);

  if (items.length === 0) return null;

  return (
    <section>
      <div className="mb-4 flex items-center gap-3 border-l-2 border-[#B99654] pl-3">
        <h2 className="text-base font-bold tracking-wide text-[#26211C]">
          Đang đọc gần đây
        </h2>
        <span className="text-xs text-[#8C8373]">({items.length})</span>
      </div>

      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
        {items.map((item) => (
          <Link
            key={`${item.bookId}-${item.chapterNumber}`}
            href={`/books/${item.bookId}/chapters/${item.chapterNumber}`}
            className="rounded-md border border-[#DDD5C8] bg-[#FBFAF7]/88 p-3 shadow-[0_5px_18px_rgba(66,52,35,0.05)] transition-all hover:border-[#B99654]/70 hover:bg-[#F4EFE6]"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="truncate text-sm font-semibold text-[#2C2825]">
                {item.bookTitle}
              </span>
              <span className="shrink-0 rounded-full bg-[#E8E0D2] px-2.5 py-1 text-[11px] font-semibold text-[#5C5449]">
                Chương {item.chapterNumber}
              </span>
            </div>
            <p className="mt-1.5 truncate text-xs text-[#7A7365]">
              {item.chapterTitle}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
