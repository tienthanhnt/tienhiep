'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getChapterPath } from '@/lib/seo';

interface RecentItem {
  bookId: number | string;
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
    <section className="max-w-lg">
      <div className="mb-1.5 flex items-center gap-2 border-l-2 border-[#B99654] pl-2">
        <h2 className="text-xs font-bold tracking-wide text-[#26211C]">
          Đang đọc gần đây
        </h2>
      </div>

      <div className="grid max-w-lg gap-1.5 sm:grid-cols-2">
        {items.map((item) => (
          <Link
            key={`${item.bookId}-${item.chapterNumber}`}
            href={getChapterPath({ id: item.bookId, title: item.bookTitle }, item.chapterNumber)}
            className="block rounded border border-[#D4A84F]/55 bg-[#FFF5D9]/85 px-2.5 py-1.5 shadow-[0_3px_10px_rgba(122,91,30,0.08)] transition-all hover:border-[#B99654] hover:bg-[#F8E8B9]"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-xs font-bold leading-5 text-[#2C2825]">
                {item.bookTitle}
              </span>
              <span className="shrink-0 rounded bg-[#2C2825] px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white">
                Chương {item.chapterNumber}
              </span>
            </div>
            <p className="mt-0.5 truncate text-[11px] leading-4 text-[#6B4F1D]">
              {item.chapterTitle}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
