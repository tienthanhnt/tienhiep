import { createHash } from "crypto";
import { NextResponse } from "next/server";

const MAX_COMMENTS_PER_BOOK = 60;
const MAX_NICKNAME_LENGTH = 40;
const MAX_CONTENT_LENGTH = 1000;
const MIN_CONTENT_LENGTH = 3;
const BOT_USER_AGENT_PATTERN = /bot|crawl|spider|slurp|facebookexternalhit|preview|monitor|uptime|vercel|headless/i;

function cleanPlainText(value: unknown, maxLength: number) {
  return String(value || "")
    .replace(/[\u0000-\u001F\u007F]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, maxLength);
}

function getClientIp(request: Request) {
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) return forwardedFor.split(",")[0]?.trim() || "";

  return (
    request.headers.get("x-real-ip") ||
    request.headers.get("cf-connecting-ip") ||
    ""
  );
}

function hashVisitor(value: string) {
  const secret =
    process.env.COMMENT_HASH_SECRET ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    "tien-hiep-lau-comments";

  return createHash("sha256")
    .update(`${secret}:${value}`)
    .digest("hex");
}

function getSupabaseConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  return { url, key };
}

function getSupabaseHeaders(key: string) {
  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
  };
}

export async function GET(
  _request: Request,
  { params }: { params: { bookId: string } }
) {
  const bookId = Number(params.bookId);
  const { url, key } = getSupabaseConfig();

  if (!Number.isInteger(bookId) || bookId <= 0) {
    return NextResponse.json({ error: "Invalid book id" }, { status: 400 });
  }

  if (!url || !key) {
    return NextResponse.json({ comments: [] }, { status: 200 });
  }

  try {
    const response = await fetch(`${url}/rest/v1/rpc/list_book_comments`, {
      method: "POST",
      headers: getSupabaseHeaders(key),
      body: JSON.stringify({
        target_book_id: bookId,
        max_rows: MAX_COMMENTS_PER_BOOK,
      }),
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json({ comments: [] }, { status: 200 });
    }

    const comments = await response.json();
    return NextResponse.json({ comments }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ comments: [] }, { status: 200 });
  }
}

export async function POST(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  const bookId = Number(params.bookId);
  const { url, key } = getSupabaseConfig();

  if (!Number.isInteger(bookId) || bookId <= 0) {
    return NextResponse.json({ error: "Truyện không hợp lệ." }, { status: 400 });
  }

  if (!url || !key) {
    return NextResponse.json({ error: "Thiếu cấu hình Supabase." }, { status: 500 });
  }

  const userAgent = request.headers.get("user-agent") || "";
  if (BOT_USER_AGENT_PATTERN.test(userAgent)) {
    return NextResponse.json({ error: "Không thể gửi bình luận lúc này." }, { status: 400 });
  }

  let payload: Record<string, unknown>;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: "Dữ liệu gửi lên không hợp lệ." }, { status: 400 });
  }

  const nickname = cleanPlainText(payload.nickname, MAX_NICKNAME_LENGTH);
  const content = cleanPlainText(payload.content, MAX_CONTENT_LENGTH);
  const ratingValue = Number(payload.rating);
  const rating = Number.isInteger(ratingValue) && ratingValue >= 1 && ratingValue <= 5
    ? ratingValue
    : null;
  const chapterNumberValue = Number(payload.chapterNumber);
  const chapterNumber = Number.isInteger(chapterNumberValue) && chapterNumberValue > 0
    ? chapterNumberValue
    : null;

  if (nickname.length < 2) {
    return NextResponse.json({ error: "Nick name cần ít nhất 2 ký tự." }, { status: 400 });
  }

  if (content.length < MIN_CONTENT_LENGTH) {
    return NextResponse.json({ error: "Bình luận cần ít nhất 3 ký tự." }, { status: 400 });
  }

  const ip = getClientIp(request);
  const visitorHash = hashVisitor(`${ip}:${userAgent.slice(0, 160)}`);
  const userAgentHash = hashVisitor(userAgent.slice(0, 240));

  try {
    const response = await fetch(`${url}/rest/v1/rpc/create_book_comment`, {
      method: "POST",
      headers: getSupabaseHeaders(key),
      body: JSON.stringify({
        target_book_id: bookId,
        target_chapter_number: chapterNumber,
        target_nickname: nickname,
        target_content: content,
        target_rating: rating,
        target_visitor_hash: visitorHash,
        target_user_agent_hash: userAgentHash,
      }),
      cache: "no-store",
    });

    if (!response.ok) {
      const errorText = await response.text();
      if (errorText.includes("COMMENT_GLOBAL_COOLDOWN")) {
        return NextResponse.json(
          { error: "Bạn gửi bình luận hơi nhanh. Vui lòng thử lại sau khoảng 2 phút." },
          { status: 429 }
        );
      }
      if (errorText.includes("COMMENT_BOOK_COOLDOWN")) {
        return NextResponse.json(
          { error: "Mỗi truyện chỉ nên gửi thêm bình luận sau khoảng 10 phút." },
          { status: 429 }
        );
      }
      if (errorText.includes("BOOK_NOT_FOUND")) {
        return NextResponse.json({ error: "Không tìm thấy truyện." }, { status: 404 });
      }

      return NextResponse.json({ error: "Không thể gửi bình luận lúc này." }, { status: 502 });
    }

    const comments = await response.json();
    const comment = Array.isArray(comments) ? comments[0] : comments;
    return NextResponse.json({ comment }, { status: 201 });
  } catch {
    return NextResponse.json({ error: "Không thể gửi bình luận lúc này." }, { status: 502 });
  }
}
