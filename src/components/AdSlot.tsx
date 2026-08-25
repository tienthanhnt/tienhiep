"use client";

import React from "react";
import { affiliateProducts } from "@/config/affiliateAds";

type AdPlacement = "home" | "chapter";

interface AdSlotProps {
  placement: AdPlacement;
}

const adProducts = affiliateProducts.filter((product) => product.href.trim().length > 0);

function formatClickCount(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("vi-VN");
}

async function trackAffiliateClick(adId: string, placement: AdPlacement) {
  const endpoint = `/api/affiliate-clicks/${encodeURIComponent(adId)}`;
  const payload = JSON.stringify({ placement });

  if (typeof navigator !== "undefined" && navigator.sendBeacon) {
    const blob = new Blob([payload], { type: "application/json" });
    navigator.sendBeacon(endpoint, blob);
    return undefined;
  }

  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload,
    keepalive: true,
  });

  if (!response.ok) return undefined;
  const data = await response.json();
  return typeof data.clickCount === "number" ? data.clickCount : undefined;
}

export default function AdSlot({ placement }: AdSlotProps) {
  const [clickCounts, setClickCounts] = React.useState<Record<string, number>>({});

  React.useEffect(() => {
    let ignore = false;

    async function loadClickCounts() {
      const entries = await Promise.all(
        adProducts.map(async (product) => {
          try {
            const response = await fetch(`/api/affiliate-clicks/${encodeURIComponent(product.id)}`);
            if (!response.ok) return [product.id, 0] as const;
            const data = await response.json();
            return [product.id, Number(data.clickCount) || 0] as const;
          } catch {
            return [product.id, 0] as const;
          }
        })
      );

      if (!ignore) {
        setClickCounts(Object.fromEntries(entries));
      }
    }

    loadClickCounts();
    return () => {
      ignore = true;
    };
  }, []);

  if (adProducts.length === 0) return null;

  const isChapter = placement === "chapter";

  return (
    <aside
      aria-label="Gợi ý phụ kiện đọc sách"
      className={`rounded-md border border-[#E6D8BD] bg-[#FBF7ED]/70 px-3 py-2.5 text-[#4A4035] shadow-[0_6px_16px_rgba(68,50,28,0.035)] ${
        isChapter ? "mt-6" : "mt-1"
      }`}
    >
      <div className="mb-2 border-b border-[#E9DEC9] pb-1.5">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#A37B34]">
            Góc đọc truyện
          </p>
          <p className="mt-0.5 text-xs text-[#746959]">
            Một vài món nhỏ giúp đọc lâu đỡ mỏi mắt.
          </p>
        </div>
      </div>

      <div className="grid gap-1.5 sm:grid-cols-2 lg:grid-cols-4">
        {adProducts.map((product) => (
          <a
            key={product.id}
            href={product.href}
            target="_blank"
            rel="nofollow sponsored noopener noreferrer"
            onClick={() => {
              setClickCounts((current) => ({
                ...current,
                [product.id]: (current[product.id] || 0) + 1,
              }));
              trackAffiliateClick(product.id, placement).then((clickCount) => {
                if (typeof clickCount === "number") {
                  setClickCounts((current) => ({ ...current, [product.id]: clickCount }));
                }
              });
            }}
            className="relative min-h-[66px] rounded border border-[#E8DDC9] bg-white/50 px-2.5 py-2 pr-12 transition-colors hover:border-[#C9A867] hover:bg-[#FFF9EA] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C9A867]/45"
          >
            <span className="absolute right-1.5 top-1.5 rounded-full border border-[#E5DAC7] bg-[#F9F1E2]/65 px-1.5 py-0.5 text-[9px] leading-none text-[#9C907F]">
              {formatClickCount(clickCounts[product.id] || 0)}
            </span>
            <span className="block text-[13px] font-semibold leading-snug text-[#2C2825]">
              {product.name}
            </span>
            <span className="mt-0.5 block text-[11px] leading-snug text-[#7F7465]">
              {product.description}
            </span>
            <span className="mt-1 inline-block text-[11px] font-semibold text-[#9A6E25]">
              Xem trên Shopee
            </span>
          </a>
        ))}
      </div>
    </aside>
  );
}
