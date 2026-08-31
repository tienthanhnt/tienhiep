"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { isIosOrInAppBrowser } from "@/lib/adGuards";

const SOCIAL_BAR_SCRIPT_ID = "adsterra-social-bar-script";
const SOCIAL_BAR_SRC =
  "https://pl31084590.profitableratecpmnetwork.com/33/d1/5d/33d15db9062b09b7bad58b10c826b4e9.js";
const LOAD_DELAY_MS = 15 * 60 * 1000;
const COOLDOWN_MS = 60 * 60 * 1000;
const LAST_SHOWN_KEY = "tien-hiep-lau:adsterra-social-bar-last-shown-at";

export default function AdsterraSocialBar() {
  const pathname = usePathname();

  useEffect(() => {
    if (!pathname.includes("/chapters/")) return;
    if (isIosOrInAppBrowser()) return;
    if (document.getElementById(SOCIAL_BAR_SCRIPT_ID)) return;

    const timeout = window.setTimeout(() => {
      if (document.getElementById(SOCIAL_BAR_SCRIPT_ID)) return;

      try {
        const lastShownAt = Number(window.localStorage.getItem(LAST_SHOWN_KEY) || 0);
        if (Date.now() - lastShownAt < COOLDOWN_MS) return;
        window.localStorage.setItem(LAST_SHOWN_KEY, String(Date.now()));
      } catch {
        // Ads should never interrupt reading if browser storage is unavailable.
      }

      const script = document.createElement("script");
      script.id = SOCIAL_BAR_SCRIPT_ID;
      script.src = SOCIAL_BAR_SRC;
      script.async = true;
      script.setAttribute("data-cfasync", "false");
      document.body.appendChild(script);
    }, LOAD_DELAY_MS);

    return () => window.clearTimeout(timeout);
  }, [pathname]);

  return null;
}
