import React from 'react';

interface AdSlotProps {
  type: 'banner' | 'sidebar' | 'inline';
  label?: string;
}

/**
 * AdSlot — Placeholder cho vị trí quảng cáo.
 * Khi có link quảng cáo thực, thay phần nội dung bên trong bằng <a> hoặc <iframe>.
 */
export default function AdSlot({ type, label }: AdSlotProps) {
  if (type === 'banner') {
    return (
      <div className="w-full h-20 md:h-24 flex items-center justify-center rounded-xl border-2 border-dashed border-[#C69C4E]/30 bg-[#EFEAD9]/60 text-[#A89C7E] text-xs font-medium tracking-wide gap-2 my-2 select-none">
        <span className="text-base opacity-60">📢</span>
        <span className="opacity-60">{label || 'Banner Quảng Cáo · 728×90'}</span>
      </div>
    );
  }

  if (type === 'sidebar') {
    return (
      <div className="w-full flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#C69C4E]/30 bg-[#EFEAD9]/60 text-[#A89C7E] text-xs font-medium tracking-wide gap-2 py-10 select-none">
        <span className="text-2xl opacity-50">📢</span>
        <span className="opacity-60">{label || 'Quảng Cáo'}</span>
        <span className="opacity-40 text-[10px]">300×250</span>
      </div>
    );
  }

  // inline — between sections
  return (
    <div className="w-full h-16 flex items-center justify-center rounded-lg border border-dashed border-[#C69C4E]/25 bg-[#EFEAD9]/40 text-[#A89C7E] text-xs gap-2 my-1 select-none">
      <span className="opacity-50">📢</span>
      <span className="opacity-50">{label || 'Quảng Cáo Nội Tuyến'}</span>
    </div>
  );
}
