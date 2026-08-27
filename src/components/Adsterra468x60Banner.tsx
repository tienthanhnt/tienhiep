"use client";

import React, { useEffect, useRef } from "react";

interface Adsterra468x60BannerProps {
  className?: string;
}

export default function Adsterra468x60Banner({ className = "" }: Adsterra468x60BannerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    containerRef.current.innerHTML = "";

    const scriptOptions = document.createElement("script");
    scriptOptions.type = "text/javascript";
    scriptOptions.innerHTML = `
      atOptions = {
        'key' : '8becb8ea89066a41b0ae0584d18514fa',
        'format' : 'iframe',
        'height' : 60,
        'width' : 468,
        'params' : {}
      };
    `;

    const scriptInvoke = document.createElement("script");
    scriptInvoke.type = "text/javascript";
    scriptInvoke.src = "https://www.highrevenueformat.com/8becb8ea89066a41b0ae0584d18514fa/invoke.js";
    scriptInvoke.async = true;

    containerRef.current.appendChild(scriptOptions);
    containerRef.current.appendChild(scriptInvoke);
  }, []);

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-[#A09688] mb-0.5">Quảng cáo</span>
      <div 
        ref={containerRef} 
        className="w-[468px] h-[60px] max-w-full bg-[#F4EFE6]/50 rounded border border-[#E6D8BD]/50 flex items-center justify-center overflow-hidden shadow-sm"
      />
    </div>
  );
}
