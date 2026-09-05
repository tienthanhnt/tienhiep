"use client";

import React, { useEffect, useRef } from "react";

interface AdsterraBannerProps {
  className?: string;
  loadDelayMs?: number;
  loadImmediately?: boolean;
}

export default function AdsterraBanner({ className = "", loadDelayMs = 0, loadImmediately = false }: AdsterraBannerProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const hasLoadedRef = useRef(false);

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    let timer: ReturnType<typeof setTimeout> | null = null;

    const loadAd = () => {
      if (hasLoadedRef.current) return;
      if (!containerRef.current) return;
      hasLoadedRef.current = true;

      // Clear previous ad if any to handle re-renders / navigation.
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
    };

    const scheduleLoad = () => {
      if (timer) return;
      timer = setTimeout(loadAd, loadDelayMs);
    };

    if (loadImmediately) {
      if (document.readyState === "complete") {
        scheduleLoad();
      } else {
        window.addEventListener("load", scheduleLoad, { once: true });
      }
      return () => {
        window.removeEventListener("load", scheduleLoad);
        if (timer) clearTimeout(timer);
      };
    }

    if (!("IntersectionObserver" in window)) {
      scheduleLoad();
      return () => {
        if (timer) clearTimeout(timer);
      };
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          observer.disconnect();
          scheduleLoad();
        }
      },
      { rootMargin: "1200px 0px" },
    );

    observer.observe(wrapper);

    return () => {
      observer.disconnect();
      if (timer) clearTimeout(timer);
    };
  }, [loadDelayMs, loadImmediately]);

  return (
    <div ref={wrapperRef} className={`flex flex-col items-center justify-center my-4 ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-[#A09688] mb-1">Quảng cáo</span>
      <div 
        ref={containerRef} 
        className="w-[160px] h-[300px] bg-[#F4EFE6]/50 rounded border border-[#E6D8BD]/50 flex items-center justify-center overflow-hidden shadow-sm"
      />
    </div>
  );
}
