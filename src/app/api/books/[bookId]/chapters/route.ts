import { NextResponse } from "next/server";
import { getNewBookPublicId, isNewBookIdentifier, queryD1 } from "@/lib/d1";

const PAGE_SIZE = 100;
const CACHE_SECONDS = 3600;

function sanitizeKeyword(value: string) {
  return value.trim().replace(/[%*_]/g, "").slice(0, 80);
}

export async function GET(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  const rawBookId = params.bookId;
  const { searchParams } = new URL(request.url);
  const page = Math.max(0, Number(searchParams.get("page") || "0") || 0);
  const query = sanitizeKeyword(searchParams.get("q") || "");

  if (isNewBookIdentifier(rawBookId)) {
    const publicId = getNewBookPublicId(rawBookId);
    if (!publicId) {
      return NextResponse.json({ error: "Invalid book id" }, { status: 400 });
    }

    try {
      const books = await queryD1<{ id: number }>(
        "SELECT id FROM books WHERE public_id = ? LIMIT 1",
        [publicId],
        CACHE_SECONDS,
      );
      const book = books[0];
      if (!book) return NextResponse.json({ chapters: [] }, { status: 200 });

      let chapters;
      if (query.length >= 2) {
        const chapterNumber = Number(query);
        if (Number.isInteger(chapterNumber)) {
          chapters = await queryD1(
            `
            SELECT id, chapter_number, title, created_at
            FROM chapters
            WHERE book_id = ? AND (title LIKE ? OR chapter_number = ?)
            ORDER BY chapter_number ASC
            LIMIT ?
            `,
            [book.id, `%${query}%`, chapterNumber, PAGE_SIZE],
            CACHE_SECONDS,
          );
        } else {
          chapters = await queryD1(
            `
            SELECT id, chapter_number, title, created_at
            FROM chapters
            WHERE book_id = ? AND title LIKE ?
            ORDER BY chapter_number ASC
            LIMIT ?
            `,
            [book.id, `%${query}%`, PAGE_SIZE],
            CACHE_SECONDS,
          );
        }
      } else {
        chapters = await queryD1(
          `
          SELECT id, chapter_number, title, created_at
          FROM chapters
          WHERE book_id = ?
          ORDER BY chapter_number ASC
          LIMIT ? OFFSET ?
          `,
          [book.id, PAGE_SIZE, page * PAGE_SIZE],
          CACHE_SECONDS,
        );
      }

      return NextResponse.json(
        { chapters },
        {
          headers: {
            "Cache-Control": `public, s-maxage=${CACHE_SECONDS}, stale-while-revalidate=86400`,
          },
        },
      );
    } catch {
      return NextResponse.json({ chapters: [] }, { status: 200 });
    }
  }

  const bookId = Number(rawBookId);
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!Number.isInteger(bookId) || bookId <= 0) {
    return NextResponse.json({ error: "Invalid book id" }, { status: 400 });
  }

  if (!url || !key) {
    return NextResponse.json({ error: "Missing Supabase config" }, { status: 500 });
  }

  const headers = {
    apikey: key,
    Authorization: `Bearer ${key}`,
  };

  try {
    let endpoint = `${url}/rest/v1/chapters?book_id=eq.${bookId}&select=id,chapter_number,title,created_at&order=chapter_number.asc`;
    const requestHeaders: Record<string, string> = { ...headers };

    if (query.length >= 2) {
      const chapterNumber = Number(query);
      const filters = [`title.ilike.*${encodeURIComponent(query)}*`];
      if (Number.isInteger(chapterNumber)) {
        filters.push(`chapter_number.eq.${chapterNumber}`);
      }
      endpoint += `&or=(${filters.join(",")})&limit=${PAGE_SIZE}`;
    } else {
      const from = page * PAGE_SIZE;
      const to = from + PAGE_SIZE - 1;
      requestHeaders.Range = `${from}-${to}`;
    }

    const response = await fetch(endpoint, {
      headers: requestHeaders,
      next: { revalidate: CACHE_SECONDS },
    });

    if (!response.ok) {
      return NextResponse.json({ chapters: [] }, { status: 200 });
    }

    const chapters = await response.json();
    return NextResponse.json(
      { chapters },
      {
        headers: {
          "Cache-Control": `public, s-maxage=${CACHE_SECONDS}, stale-while-revalidate=86400`,
        },
      }
    );
  } catch {
    return NextResponse.json({ chapters: [] }, { status: 200 });
  }
}
