import React from "react";
import { affiliateProducts } from "@/config/affiliateAds";

type AdPlacement = "home" | "chapter";

interface AdSlotProps {
  placement: AdPlacement;
}

const adProducts = affiliateProducts.filter((product) => product.href.trim().length > 0);

export default function AdSlot({ placement }: AdSlotProps) {
  if (adProducts.length === 0) return null;

  const isChapter = placement === "chapter";

  return (
    <aside
      aria-label="Gợi ý phụ kiện đọc sách"
      className={`rounded-md border border-[#E6D8BD] bg-[#FBF7ED]/75 px-4 py-3 text-[#4A4035] shadow-[0_8px_20px_rgba(68,50,28,0.04)] ${
        isChapter ? "mt-7" : "mt-1"
      }`}
    >
      <div className="mb-2 flex items-baseline justify-between gap-3 border-b border-[#E9DEC9] pb-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#A37B34]">
            Góc đọc truyện
          </p>
          <p className="mt-0.5 text-sm text-[#746959]">
            Một vài món nhỏ giúp đọc lâu đỡ mỏi mắt.
          </p>
        </div>
        <span className="shrink-0 text-[10px] text-[#AAA093]">
          Liên kết giới thiệu
        </span>
      </div>

      <div className="grid gap-2 md:grid-cols-3">
        {adProducts.map((product) => (
          <a
            key={product.name}
            href={product.href}
            target="_blank"
            rel="nofollow sponsored noopener noreferrer"
            className="rounded border border-[#E8DDC9] bg-white/55 px-3 py-2 transition-colors hover:border-[#C9A867] hover:bg-[#FFF9EA] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C9A867]/45"
          >
            <span className="block text-sm font-semibold text-[#2C2825]">
              {product.name}
            </span>
            <span className="mt-1 block text-xs leading-relaxed text-[#7F7465]">
              {product.description}
            </span>
            <span className="mt-2 inline-block text-xs font-semibold text-[#9A6E25]">
              Xem trên Shopee
            </span>
          </a>
        ))}
      </div>
    </aside>
  );
}
