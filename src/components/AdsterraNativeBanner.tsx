"use client";

import React, { useEffect, useRef } from "react";

interface AdsterraNativeBannerProps {
  className?: string;
}

export default function AdsterraNativeBanner({ className = "" }: AdsterraNativeBannerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const containerId = "container-4b23181504c4526932f93943c57faf5d";
    containerRef.current.innerHTML = "";

    const targetDiv = document.createElement("div");
    targetDiv.id = containerId;
    containerRef.current.appendChild(targetDiv);

    const scriptInvoke = document.createElement("script");
    scriptInvoke.type = "text/javascript";
    scriptInvoke.src = "https://pl31049429.profitableratecpmnetwork.com/4b23181504c4526932f93943c57faf5d/invoke.js";
    scriptInvoke.async = true;
    scriptInvoke.setAttribute("data-cfasync", "false");

    containerRef.current.appendChild(scriptInvoke);
  }, []);

  return (
    <div className={`flex flex-col items-center justify-center my-6 w-full ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-[#A09688] mb-1">Gợi ý tài trợ</span>
      <div 
        ref={containerRef} 
        className="w-full min-h-[100px] bg-[#FBF7ED]/60 rounded-md border border-[#E6D8BD] p-2 flex items-center justify-center shadow-sm overflow-hidden"
      />
    </div>
  );
}
