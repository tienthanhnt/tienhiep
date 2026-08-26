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
const RECENT_READING_LIMIT = 1;

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
      <div className="mb-1.5 flex items-center gap-2 border-l-2 border-[#B99654] pl-2">
        <h2 className="text-xs font-bold tracking-wide text-[#26211C]">
          Đang đọc gần đây
        </h2>
      </div>

      <div className="max-w-sm">
        {items.map((item) => (
          <Link
            key={`${item.bookId}-${item.chapterNumber}`}
            href={`/books/${item.bookId}/chapters/${item.chapterNumber}`}
            className="block rounded border border-[#DDD5C8] bg-[#FBFAF7]/70 px-2.5 py-1.5 shadow-[0_3px_10px_rgba(66,52,35,0.035)] transition-all hover:border-[#B99654]/70 hover:bg-[#F4EFE6]"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-[11px] font-semibold text-[#2C2825]">
                {item.bookTitle}
              </span>
              <span className="shrink-0 rounded bg-[#E8E0D2] px-1.5 py-0.5 text-[9px] font-semibold text-[#5C5449]">
                Chương {item.chapterNumber}
              </span>
            </div>
            <p className="mt-0.5 truncate text-[10px] text-[#7A7365]">
              {item.chapterTitle}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
