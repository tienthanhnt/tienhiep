"use client";

import React, { useEffect, useRef } from "react";

interface AdsterraBannerProps {
  className?: string;
}

export default function AdsterraBanner({ className = "" }: AdsterraBannerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clear previous ad if any to handle re-renders / navigation
    containerRef.current.innerHTML = "";

    const scriptOptions = document.createElement("script");
    scriptOptions.type = "text/javascript";
    scriptOptions.innerHTML = `
      atOptions = {
        'key' : 'f1385a97a194ae76e78d55e84a245780',
        'format' : 'iframe',
        'height' : 300,
        'width' : 160,
        'params' : {}
      };
    `;

    const scriptInvoke = document.createElement("script");
    scriptInvoke.type = "text/javascript";
    scriptInvoke.src = "https://www.highrevenueformat.com/f1385a97a194ae76e78d55e84a245780/invoke.js";
    scriptInvoke.async = true;

    containerRef.current.appendChild(scriptOptions);
    containerRef.current.appendChild(scriptInvoke);
  }, []);

  return (
    <div className={`flex flex-col items-center justify-center my-4 ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-[#A09688] mb-1">Quảng cáo</span>
      <div 
        ref={containerRef} 
        className="w-[160px] h-[300px] bg-[#F4EFE6]/50 rounded border border-[#E6D8BD]/50 flex items-center justify-center overflow-hidden shadow-sm"
      />
    </div>
  );
}
