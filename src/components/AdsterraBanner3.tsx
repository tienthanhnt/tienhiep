"use client";

import React, { useEffect, useRef } from "react";

interface AdsterraBanner3Props {
  className?: string;
}

export default function AdsterraBanner3({ className = "" }: AdsterraBanner3Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    containerRef.current.innerHTML = "";

    const scriptOptions = document.createElement("script");
    scriptOptions.type = "text/javascript";
    scriptOptions.innerHTML = `
      atOptions = {
        'key' : '8b4b80cd8c534c3b8c283ffd0dd63bae',
        'format' : 'iframe',
        'height' : 90,
        'width' : 728,
        'params' : {}
      };
    `;

    const scriptInvoke = document.createElement("script");
    scriptInvoke.type = "text/javascript";
    scriptInvoke.src = "https://www.highrevenueformat.com/8b4b80cd8c534c3b8c283ffd0dd63bae/invoke.js";
    scriptInvoke.async = true;

    containerRef.current.appendChild(scriptOptions);
    containerRef.current.appendChild(scriptInvoke);
  }, []);

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-[#A09688] mb-0.5">Quảng cáo</span>
      <div
        ref={containerRef}
        className="w-[728px] h-[90px] max-w-full bg-[#F4EFE6]/50 rounded border border-[#E6D8BD]/50 flex items-center justify-center overflow-hidden shadow-sm"
      />
    </div>
  );
}
