import { NextResponse } from "next/server";

const BOT_USER_AGENT_PATTERN = /bot|crawl|spider|slurp|facebookexternalhit|preview|monitor|uptime|vercel|headless/i;

export async function POST(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  const bookId = Number(params.bookId);
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!Number.isInteger(bookId) || bookId <= 0) {
    return NextResponse.json({ error: "Invalid book id" }, { status: 400 });
  }

  if (!url || !key) {
    return NextResponse.json({ error: "Missing Supabase config" }, { status: 500 });
  }

  const userAgent = request.headers.get("user-agent") || "";
  if (BOT_USER_AGENT_PATTERN.test(userAgent)) {
    return NextResponse.json({ skipped: true });
  }

  try {
    const response = await fetch(`${url}/rest/v1/rpc/increment_book_view`, {
      method: "POST",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ target_book_id: bookId }),
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json({ error: "Could not record view" }, { status: 502 });
    }

    const viewCount = await response.json();
    return NextResponse.json({ viewCount });
  } catch {
    return NextResponse.json({ error: "Could not record view" }, { status: 502 });
  }
}
