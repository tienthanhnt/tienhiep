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
    <Link href={`/books/${id}`} className="group flex flex-col gap-2">
      {/* Cover: fixed small height, compact */}
      <div className="relative w-full h-36 overflow-hidden rounded-md shadow border border-[#C69C4E]/25 group-hover:border-[#C69C4E]/70 transition-all duration-300">
        <img
          src={coverUrl}
          alt={title}
          className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-500"
        />

        {/* Rating Badge */}
        <div className="absolute top-1.5 left-1.5 bg-[#181D27]/80 backdrop-blur-sm text-[#D4AF37] text-[10px] font-bold px-1.5 py-0.5 rounded-full flex items-center gap-0.5 shadow-sm">
          ⭐ {rating ? Number(rating).toFixed(1) : "8.0"}
        </div>

        {/* Status Tag */}
        <div className="absolute bottom-1.5 right-1.5">
          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full border backdrop-blur-sm ${
            status === 'Hoàn thành'
              ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40'
              : 'bg-amber-950/80 text-amber-300 border-amber-500/40'
          }`}>
            {status}
          </span>
        </div>
      </div>

      <div>
        <h3 className="font-semibold text-xs text-[#2C2825] line-clamp-2 leading-snug group-hover:text-[#A37B34] transition-colors">
          {title}
        </h3>
        <p className="text-[10px] text-[#7A7365] mt-0.5 truncate">{author}</p>
        <div className="text-[10px] text-[#9C8E7E] mt-1 border-t border-[#E8E0D2] pt-1">
          {chapterCount} chương
        </div>
      </div>
    </Link>
  );
}
