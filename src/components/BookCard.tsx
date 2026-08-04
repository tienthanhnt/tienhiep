import React from 'react';
import Link from 'next/link';

interface BookCardProps {
  id: number;
  title: string;
  author: string;
  chapterCount: number;
  rating: number;
  status: 'Đang ra' | 'Hoàn thành';
  coverUrl: string;
}

export default function BookCard({ id, title, author, chapterCount, rating, status, coverUrl }: BookCardProps) {
  return (
    <Link href={`/books/${id}`} className="group flex flex-col gap-2.5">
      {/* Cover: proper book ratio 2:3 (portrait) */}
      <div className="relative w-full aspect-[2/3] overflow-hidden rounded-md shadow-md border border-[#C69C4E]/30 group-hover:border-[#C69C4E]/70 group-hover:shadow-lg transition-all duration-300">
        <img
          src={coverUrl}
          alt={title}
          className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-500"
        />

        {/* Rating Badge */}
        <div className="absolute top-2 left-2 bg-[#181D27]/85 backdrop-blur-sm text-[#D4AF37] text-[11px] font-bold px-2 py-0.5 rounded-full flex items-center gap-0.5 shadow">
          ⭐ {rating ? Number(rating).toFixed(1) : "8.0"}
        </div>

        {/* Status Tag */}
        <div className="absolute bottom-2 right-2">
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border backdrop-blur-sm ${
            status === 'Hoàn thành'
              ? 'bg-emerald-950/85 text-emerald-300 border-emerald-500/40'
              : 'bg-amber-950/85 text-amber-300 border-amber-500/40'
          }`}>
            {status}
          </span>
        </div>

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      </div>

      <div>
        <h3 className="font-semibold text-sm text-[#2C2825] line-clamp-2 leading-snug group-hover:text-[#A37B34] transition-colors">
          {title}
        </h3>
        <p className="text-xs text-[#7A7365] mt-0.5 truncate">{author}</p>
        <div className="text-xs text-[#9C8E7E] mt-1.5 border-t border-[#E8E0D2] pt-1.5">
          📜 {chapterCount} chương
        </div>
      </div>
    </Link>
  );
}
