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
      {/* Cover */}
      <div className="relative w-full aspect-[2/3] overflow-hidden rounded-lg shadow-sm group-hover:shadow-md transition-shadow duration-300">
        <img
          src={coverUrl}
          alt={title}
          className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-500"
        />

        {/* Status Tag (Top-Left) */}
        <div className="absolute top-2 left-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded shadow-sm ${
            status === 'Hoàn thành'
              ? 'bg-[#E6F4EA] text-[#137333]'
              : 'bg-[#FFF3E0] text-[#E65100]'
          }`}>
            {status === 'Hoàn thành' ? 'HOÀN' : 'ĐANG RA'}
          </span>
        </div>

        {/* Rating Badge (Bottom-Right, subtle) */}
        <div className="absolute bottom-2 right-2 bg-black/60 backdrop-blur-sm text-white text-[10px] font-medium px-1.5 py-0.5 rounded flex items-center gap-1">
          ⭐ {rating ? Number(rating).toFixed(1) : "8.0"}
        </div>
      </div>

      <div className="mt-1 flex flex-col">
        <h3 className="font-bold text-[13px] md:text-sm text-[#2C2825] line-clamp-2 leading-tight group-hover:text-[#D9730D] transition-colors">
          {title}
        </h3>
        
        <div className="flex items-center text-[11px] md:text-xs text-[#7A7365] mt-1.5 font-medium truncate">
          <span className="truncate">{author}</span>
          <span className="mx-1.5 opacity-50">•</span>
          <span className="shrink-0">{chapterCount} chương</span>
        </div>
      </div>
    </Link>
  );
}
