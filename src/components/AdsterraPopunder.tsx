"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface AdsterraPopunderProps {
  nextClickCount: number;
}

const POPUNDER_SCRIPT_ID = "adsterra-popunder-script";
const POPUNDER_SRC =
  "https://pl31053534.profitableratecpmnetwork.com/12/ca/fc/12cafc36ee3c806ecff9e8d246784869.js";
const NEXT_CHAPTER_EVENT = "tien-hiep-lau:next-chapter-click";
const READ_DELAY_MS = 35 * 1000;
const COOLDOWN_MS = 24 * 60 * 60 * 1000;
const LAST_SHOWN_KEY = "tien-hiep-lau:adsterra-pop-last-shown-at";
const READ_ELIGIBLE_KEY = "tien-hiep-lau:adsterra-pop-read-eligible-at";

export default function AdsterraPopunder({ nextClickCount }: AdsterraPopunderProps) {
  const [readEligible, setReadEligible] = useState(false);
  const shownInThisPage = useRef(false);

  const tryLoadPopunder = useCallback((clickCount = nextClickCount) => {
    if (shownInThisPage.current || !readEligible || clickCount < 2) return;
    if (document.getElementById(POPUNDER_SCRIPT_ID)) return;

    try {
      const lastShownAt = Number(window.localStorage.getItem(LAST_SHOWN_KEY) || 0);
      if (Date.now() - lastShownAt < COOLDOWN_MS) return;
      window.localStorage.setItem(LAST_SHOWN_KEY, String(Date.now()));
    } catch {
      // If storage is blocked, still avoid repeated injection inside this page.
    }

    shownInThisPage.current = true;
    const script = document.createElement("script");
    script.id = POPUNDER_SCRIPT_ID;
    script.src = POPUNDER_SRC;
    script.async = true;
    script.setAttribute("data-cfasync", "false");
    document.body.appendChild(script);
  }, [nextClickCount, readEligible]);

  useEffect(() => {
    let mounted = true;
    setReadEligible(false);

    const timeout = window.setTimeout(() => {
      if (!mounted) return;
      setReadEligible(true);
      try {
        window.localStorage.setItem(READ_ELIGIBLE_KEY, String(Date.now()));
      } catch {
        // Popunder gating should not interrupt reading.
      }
    }, READ_DELAY_MS);

    return () => {
      mounted = false;
      window.clearTimeout(timeout);
    };
  }, []);

  useEffect(() => {
    const onNextChapterClick = (event: Event) => {
      const clickCount = event instanceof CustomEvent ? Number(event.detail?.clickCount || 0) : nextClickCount;
      tryLoadPopunder(clickCount);
    };
    window.addEventListener(NEXT_CHAPTER_EVENT, onNextChapterClick);
    return () => window.removeEventListener(NEXT_CHAPTER_EVENT, onNextChapterClick);
  }, [nextClickCount, tryLoadPopunder]);

  useEffect(() => {
    tryLoadPopunder();
  }, [tryLoadPopunder]);

  return null;
}

export { NEXT_CHAPTER_EVENT };
