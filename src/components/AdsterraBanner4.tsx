"use client";

import React, { useEffect, useRef } from "react";

interface AdsterraBanner4Props {
  className?: string;
  loadDelayMs?: number;
  loadImmediately?: boolean;
}

export default function AdsterraBanner4({ className = "", loadDelayMs = 0, loadImmediately = false }: AdsterraBanner4Props) {
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
    <div ref={wrapperRef} className={`flex flex-col items-center justify-center ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-[#A09688] mb-0.5">Quảng cáo</span>
      <div
        ref={containerRef}
        className="w-[300px] h-[250px] max-w-full bg-[#F4EFE6]/50 rounded border border-[#E6D8BD]/50 flex items-center justify-center overflow-hidden shadow-sm"
      />
    </div>
  );
}
