import { NextResponse } from "next/server";
import { executeD1, getNewBookPublicId, isNewBookIdentifier } from "@/lib/d1";

const BOT_USER_AGENT_PATTERN = /bot|crawl|spider|slurp|facebookexternalhit|preview|monitor|uptime|vercel|headless/i;

export async function POST(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  const userAgent = request.headers.get("user-agent") || "";
  if (BOT_USER_AGENT_PATTERN.test(userAgent)) {
    return NextResponse.json({ skipped: true });
  }

  if (isNewBookIdentifier(params.bookId)) {
    const publicId = getNewBookPublicId(params.bookId);
    if (!publicId) {
      return NextResponse.json({ error: "Invalid book id" }, { status: 400 });
    }
    try {
      const rows = await executeD1<{ view_count: number }>(
        `
        UPDATE books
        SET view_count = COALESCE(view_count, 0) + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE public_id = ?
        RETURNING view_count
        `,
        [publicId],
      );
      if (!rows[0]) {
        return NextResponse.json({ error: "Book not found" }, { status: 404 });
      }
      return NextResponse.json({ viewCount: Number(rows[0].view_count || 0) });
    } catch (error) {
      console.error("Could not record D1 book view:", error);
      return NextResponse.json({ error: "Could not record view" }, { status: 502 });
    }
  }

  const bookId = Number(params.bookId);
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!Number.isInteger(bookId) || bookId <= 0) {
    return NextResponse.json({ error: "Invalid book id" }, { status: 400 });
  }

  if (!url || !key) {
    return NextResponse.json({ error: "Missing Supabase config" }, { status: 500 });
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
