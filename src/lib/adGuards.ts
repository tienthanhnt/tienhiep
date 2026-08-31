const IN_APP_BROWSER_PATTERN =
  /FBAN|FBAV|FB_IAB|Instagram|Line\/|MicroMessenger|TikTok|Bytedance|Twitter|Snapchat|Pinterest|LinkedInApp|Zalo/i;

export function isMobileViewport() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(max-width: 767px)").matches;
}

export function isIosOrInAppBrowser() {
  if (typeof navigator === "undefined") return false;

  const userAgent = navigator.userAgent || "";
  const platform = navigator.platform || "";
  const isIos =
    /iPad|iPhone|iPod/i.test(userAgent) ||
    (platform === "MacIntel" && navigator.maxTouchPoints > 1);

  return isIos || IN_APP_BROWSER_PATTERN.test(userAgent);
}
