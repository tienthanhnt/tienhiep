"use client";

import React, { useEffect, useRef } from "react";

interface AdsterraBanner2Props {
  className?: string;
}

export default function AdsterraBanner2({ className = "" }: AdsterraBanner2Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    containerRef.current.innerHTML = "";

    const scriptOptions = document.createElement("script");
    scriptOptions.type = "text/javascript";
    scriptOptions.innerHTML = `
      atOptions = {
        'key' : '8bab8eb045a61cd0e1ff6b7c16260d72',
        'format' : 'iframe',
        'height' : 50,
        'width' : 320,
        'params' : {}
      };
    `;

    const scriptInvoke = document.createElement("script");
    scriptInvoke.type = "text/javascript";
    scriptInvoke.src = "https://www.highrevenueformat.com/8bab8eb045a61cd0e1ff6b7c16260d72/invoke.js";
    scriptInvoke.async = true;

    containerRef.current.appendChild(scriptOptions);
    containerRef.current.appendChild(scriptInvoke);
  }, []);

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-[#A09688] mb-0.5">Quảng cáo</span>
      <div
        ref={containerRef}
        className="w-[320px] h-[50px] max-w-full bg-[#F4EFE6]/50 rounded border border-[#E6D8BD]/50 flex items-center justify-center overflow-hidden shadow-sm"
      />
    </div>
  );
}
