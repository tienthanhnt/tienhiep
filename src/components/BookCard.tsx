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
      <div className="relative aspect-[2/3] overflow-hidden rounded-lg shadow-md border border-[#C69C4E]/30 group-hover:border-[#C69C4E] transition-all duration-300">
        <img 
          src={coverUrl} 
          alt={title} 
          className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-500"
        />
        
        {/* Rating Badge */}
        <div className="absolute top-2 left-2 bg-[#181D27]/85 backdrop-blur-md text-[#D4AF37] border border-[#C69C4E]/40 text-xs font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
          <span>⭐</span> {rating ? Number(rating).toFixed(1) : "8.0"}
        </div>

        {/* Status Tag */}
        <div className="absolute bottom-2 right-2">
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border backdrop-blur-md ${
            status === 'Hoàn thành' 
              ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40' 
              : 'bg-amber-950/80 text-amber-300 border-amber-500/40'
          }`}>
            {status}
          </span>
        </div>
      </div>

      <div className="px-1">
        <h3 className="font-bold text-sm text-[#2C2825] line-clamp-2 leading-snug group-hover:text-[#A37B34] transition-colors">
          {title}
        </h3>
        <p className="text-xs text-[#7A7365] mt-1 truncate">✍️ {author}</p>
        <div className="flex items-center justify-between text-[11px] text-[#8C8373] mt-1.5 font-medium border-t border-[#E8E0D2] pt-1.5">
          <span>📜 {chapterCount} chương</span>
          <span className="text-[#A37B34]">Đọc ngay &rarr;</span>
        </div>
      </div>
    </Link>
  );
}
