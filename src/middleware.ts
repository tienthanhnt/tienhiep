import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const ALLOWED_SEARCH_BOTS = [
  "googlebot",
  "bingbot",
  "slurp",
  "duckduckbot",
  "baiduspider",
  "yandexbot",
  "coccocbot",
];

const BLOCKED_BOTS = [
  "ahrefsbot",
  "semrushbot",
  "mj12bot",
  "dotbot",
  "petalbot",
  "bytespider",
  "claudebot",
  "gptbot",
  "ccbot",
  "amazonbot",
  "dataforseobot",
  "barkrowler",
  "blexbot",
  "seekportbot",
  "serpstatbot",
  "seznambot",
  "megaindex",
  "scrapy",
  "python-requests",
  "go-http-client",
  "wget",
  "curl",
];

function includesAny(value: string, needles: string[]) {
  return needles.some((needle) => value.includes(needle));
}

export function middleware(request: NextRequest) {
  const userAgent = (request.headers.get("user-agent") || "").toLowerCase();

  if (includesAny(userAgent, ALLOWED_SEARCH_BOTS)) {
    return NextResponse.next();
  }

  if (includesAny(userAgent, BLOCKED_BOTS)) {
    return new NextResponse("Forbidden", {
      status: 403,
      headers: {
        "Cache-Control": "public, max-age=3600",
      },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/books/:path*",
    "/api/books/:path*",
    "/sitemap.xml",
  ],
};
