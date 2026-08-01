import React from 'react';

interface BookCardProps {
  title: string;
  author: string;
  chapterCount: number;
  rating: number;
  status: 'Đang ra' | 'Hoàn thành';
  coverUrl: string;
}

export default function BookCard({ title, author, chapterCount, rating, status, coverUrl }: BookCardProps) {
  return (
    <div className="group flex flex-col gap-2 cursor-pointer">
      <div className="relative aspect-[2/3] overflow-hidden rounded-md shadow-sm group-hover:shadow-md transition-shadow">
        {/* Using a standard img tag for simplicity, in a real app you'd use next/image */}
        <img 
          src={coverUrl} 
          alt={title} 
          className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-300"
        />
        <div className="absolute top-2 left-2 bg-blue-600 text-white text-xs font-bold px-1.5 py-0.5 rounded">
          {rating.toFixed(1)}
        </div>
      </div>
      <div>
        <h3 className="font-semibold text-sm line-clamp-2 leading-tight group-hover:text-blue-600 transition-colors">
          {title}
        </h3>
        <p className="text-xs text-gray-500 mt-1 truncate">{author}</p>
        <div className="flex items-center justify-between text-xs text-gray-500 mt-1">
          <span>{chapterCount} chương</span>
          <span className={status === 'Hoàn thành' ? 'text-green-600 font-medium' : 'text-orange-500 font-medium'}>{status}</span>
        </div>
      </div>
    </div>
  );
}
