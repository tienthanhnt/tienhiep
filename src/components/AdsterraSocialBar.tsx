"use client";

import { useEffect } from "react";

const SOCIAL_BAR_SCRIPT_ID = "adsterra-social-bar-script";
const SOCIAL_BAR_SRC =
  "https://pl31084590.profitableratecpmnetwork.com/33/d1/5d/33d15db9062b09b7bad58b10c826b4e9.js";
const LOAD_DELAY_MS = 8000;

export default function AdsterraSocialBar() {
  useEffect(() => {
    if (document.getElementById(SOCIAL_BAR_SCRIPT_ID)) return;

    const timeout = window.setTimeout(() => {
      if (document.getElementById(SOCIAL_BAR_SCRIPT_ID)) return;

      const script = document.createElement("script");
      script.id = SOCIAL_BAR_SCRIPT_ID;
      script.src = SOCIAL_BAR_SRC;
      script.async = true;
      script.setAttribute("data-cfasync", "false");
      document.body.appendChild(script);
    }, LOAD_DELAY_MS);

    return () => window.clearTimeout(timeout);
  }, []);

  return null;
}
