"use client";

import React, { useEffect, useRef } from "react";

interface Adsterra160x600BannerProps {
  className?: string;
}

export default function Adsterra160x600Banner({ className = "" }: Adsterra160x600BannerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    containerRef.current.innerHTML = "";

    const scriptOptions = document.createElement("script");
    scriptOptions.type = "text/javascript";
    scriptOptions.innerHTML = `
      atOptions = {
        'key' : '5b8dd837ca72dfe85da7b561078b8b5c',
        'format' : 'iframe',
        'height' : 600,
        'width' : 160,
        'params' : {}
      };
    `;

    const scriptInvoke = document.createElement("script");
    scriptInvoke.type = "text/javascript";
    scriptInvoke.src = "https://www.highrevenueformat.com/5b8dd837ca72dfe85da7b561078b8b5c/invoke.js";
    scriptInvoke.async = true;

    containerRef.current.appendChild(scriptOptions);
    containerRef.current.appendChild(scriptInvoke);
  }, []);

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-[#A09688] mb-0.5">Quảng cáo</span>
      <div 
        ref={containerRef} 
        className="w-[160px] h-[600px] max-w-full bg-[#F4EFE6]/50 rounded border border-[#E6D8BD]/50 flex items-center justify-center overflow-hidden shadow-sm"
      />
    </div>
  );
}
