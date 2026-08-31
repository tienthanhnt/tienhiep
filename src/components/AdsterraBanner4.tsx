"use client";

import React, { useEffect, useRef, useState } from "react";
import { isMobileViewport } from "@/lib/adGuards";

interface AdsterraBanner4Props {
  className?: string;
}

export default function AdsterraBanner4({ className = "" }: AdsterraBanner4Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [canLoadAd, setCanLoadAd] = useState(false);

  useEffect(() => {
    if (isMobileViewport()) return;
    setCanLoadAd(true);
  }, []);

  useEffect(() => {
    if (!canLoadAd) return;
    if (!containerRef.current) return;

    containerRef.current.innerHTML = "";

    const scriptOptions = document.createElement("script");
    scriptOptions.type = "text/javascript";
    scriptOptions.innerHTML = `
      atOptions = {
        'key' : '7e0c3d059c2e2a6efdb2dcbf740c0940',
        'format' : 'iframe',
        'height' : 250,
        'width' : 300,
        'params' : {}
      };
    `;

    const scriptInvoke = document.createElement("script");
    scriptInvoke.type = "text/javascript";
    scriptInvoke.src = "https://www.highrevenueformat.com/7e0c3d059c2e2a6efdb2dcbf740c0940/invoke.js";
    scriptInvoke.async = true;

    containerRef.current.appendChild(scriptOptions);
    containerRef.current.appendChild(scriptInvoke);
  }, [canLoadAd]);

  if (!canLoadAd) return null;

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-[#A09688] mb-0.5">Quảng cáo</span>
      <div
        ref={containerRef}
        className="w-[300px] h-[250px] max-w-full bg-[#F4EFE6]/50 rounded border border-[#E6D8BD]/50 flex items-center justify-center overflow-hidden shadow-sm"
      />
    </div>
  );
}
