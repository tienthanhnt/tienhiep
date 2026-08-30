import React from 'react';
import Link from 'next/link';
import { formatCompactNumber } from '@/lib/format';
import { getBookPath } from '@/lib/seo';

interface BookCardProps {
  id: number;
  title: string;
  author: string;
  chapterCount: number;
  status: 'Đang ra' | 'Hoàn thành';
  coverUrl: string;
  genres?: string;
  sourceType?: string;
  viewCount?: number;
}

function splitTags(value?: string) {
  return (value || "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export default function BookCard({ id, title, author, chapterCount, status, coverUrl, genres, sourceType, viewCount }: BookCardProps) {
  const tags = [...(sourceType ? [sourceType] : []), ...splitTags(genres)].slice(0, 3);
  const bookPath = getBookPath({ id, title });

  return (
    <Link href={bookPath} className="group flex flex-col gap-2.5 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-[#B99654]/50">
      {/* Cover */}
      <div className="relative w-full aspect-[2/3] overflow-hidden rounded-md border border-[#D8CDBB] bg-[#EFE9DC] shadow-[0_4px_14px_rgba(66,52,35,0.08)] transition-all duration-200 group-hover:-translate-y-0.5 group-hover:border-[#B99654]/70 group-hover:shadow-[0_10px_24px_rgba(66,52,35,0.14)]">
        <img
          src={coverUrl}
          alt={title}
          loading="lazy"
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.025]"
        />
        <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/30 to-transparent opacity-80" />
      </div>

      <div className="mt-1 flex flex-col min-h-[70px]">
        <h3 className="font-semibold text-[13px] md:text-sm text-[#2C2825] line-clamp-2 leading-snug group-hover:text-[#7A5B1E] transition-colors">
          {title}
        </h3>
        
        <div className="flex items-center text-[11px] md:text-xs text-[#7A7365] mt-1.5 font-medium truncate leading-none">
          <span className="truncate">{author}</span>
          <span className="mx-1.5 opacity-50">•</span>
          <span className="shrink-0">{chapterCount} chương</span>
        </div>

        <div className="mt-1.5 text-[11px] md:text-xs text-[#8C8373]">
          {formatCompactNumber(viewCount)} lượt đọc
        </div>

        <div className="mt-2 flex flex-wrap gap-1.5">
          <span className={`inline-flex rounded border px-2 py-0.5 text-[10px] font-bold leading-none ${
            status === 'Hoàn thành'
              ? 'border-[#B7DEC2] bg-[#E6F4EA] text-[#137333]'
              : 'border-[#F1D0A8] bg-[#FFF3E0] text-[#B85300]'
          }`}>
            {status}
          </span>
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex rounded border border-[#DDD5C8] bg-[#FBFAF7] px-2 py-0.5 text-[10px] font-semibold leading-none text-[#6B6357]"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </Link>
  );
}
