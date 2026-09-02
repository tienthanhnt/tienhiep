import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import ChapterReader from '@/components/ChapterReader';
import { gunzipSync } from 'zlib';
import { getNewBookPublicId, isNewBookIdentifier, queryD1 } from '@/lib/d1';
import { resolveBookId } from '@/lib/books';
import { buildChapterDescription, getChapterPath, getCleanChapterTitle, getSiteUrl, SITE_NAME } from '@/lib/seo';

const CHAPTER_PAGE_REVALIDATE_SECONDS = 86400;
const CHAPTER_CONTENT_REVALIDATE_SECONDS = 604800;

export const revalidate = CHAPTER_PAGE_REVALIDATE_SECONDS;
export const runtime = 'nodejs';

interface Chapter {
  id: number | string;
  book_id: number;
  chapter_number: number;
  title: string;
  content_html?: string | null;
  content_url?: string | null;
  content_path?: string | null;
}

interface Book {
  id: number | string;
  internal_id?: number;
  title: string;
  chapter_count: number;
  cover_url?: string | null;
}

interface D1BookRow {
  id: number;
  public_id?: string | null;
  title: string;
  chapter_count: number;
  cover_url?: string | null;
}

interface D1ChapterRow {
  id: number;
  book_id: number;
  chapter_number: number;
  title: string;
  content_html?: string | null;
  content_url?: string | null;
  content_path?: string | null;
}

async function fetchChapterContent(chapter: Chapter) {
  if (!chapter.content_url) return "";

  const resContent = await fetch(chapter.content_url, {
    next: { revalidate: CHAPTER_CONTENT_REVALIDATE_SECONDS },
  });
  if (!resContent.ok) return "";

  const isCompressed =
    chapter.content_path?.endsWith(".gz") || chapter.content_url.endsWith(".gz");

  if (!isCompressed) {
    return resContent.text();
  }

  const compressed = Buffer.from(await resContent.arrayBuffer());
  return gunzipSync(compressed).toString("utf-8");
}

async function getChapterData(bookIdentifier: string, chapterNum: string) {
  if (isNewBookIdentifier(bookIdentifier)) {
    const publicId = getNewBookPublicId(bookIdentifier);
    if (!publicId) return null;

    try {
      const books = await queryD1<D1BookRow>(
        "SELECT id, public_id, title, chapter_count, cover_url FROM books WHERE public_id = ? LIMIT 1",
        [publicId],
        CHAPTER_PAGE_REVALIDATE_SECONDS,
      );
      const book = books[0];
      if (!book) return null;

      const chapters = await queryD1<D1ChapterRow>(
        `
        SELECT id, book_id, chapter_number, title, content_html, content_url, content_path
        FROM chapters
        WHERE book_id = ? AND chapter_number = ?
        LIMIT 1
        `,
        [book.id, Number(chapterNum)],
        CHAPTER_PAGE_REVALIDATE_SECONDS,
      );
      const chapter = chapters[0];
      if (!chapter) return null;

      let contentHtml = chapter.content_html || "";
      if (!contentHtml && chapter.content_url) {
        contentHtml = await fetchChapterContent(chapter);
      }
      if (!contentHtml) return null;

      return {
        book: {
          ...book,
          id: book.public_id || `new-${book.id}`,
          internal_id: book.id,
        } as Book,
        chapter,
        contentHtml,
      };
    } catch (err) {
      console.error("Error fetching D1 chapter:", err);
      return null;
    }
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) return null;
  const bookId = await resolveBookId(bookIdentifier);
  if (!bookId) return null;

  try {
    const headers = { apikey: key, Authorization: `Bearer ${key}` };
    const [resBook, resChapter] = await Promise.all([
      fetch(`${url}/rest/v1/books?id=eq.${bookId}&select=id,title,chapter_count`, {
        headers,
        next: { revalidate: CHAPTER_PAGE_REVALIDATE_SECONDS },
      }),
      fetch(
        `${url}/rest/v1/chapters?book_id=eq.${bookId}&chapter_number=eq.${chapterNum}&select=id,book_id,chapter_number,title,content_html,content_url,content_path`,
        {
          headers,
          next: { revalidate: CHAPTER_PAGE_REVALIDATE_SECONDS },
        }
      ),
    ]);

    if (!resBook.ok) return null;
    const books = await resBook.json();
    if (!books || books.length === 0) return null;

    if (!resChapter.ok) return null;
    const chapters = await resChapter.json();
    if (!chapters || chapters.length === 0) return null;

    const chapter = chapters[0] as Chapter;
    let contentHtml = chapter.content_html || "";

    if (!contentHtml && chapter.content_url) {
      contentHtml = await fetchChapterContent(chapter);
    }

    if (!contentHtml) return null;

    return {
      book: books[0] as Book,
      chapter,
      contentHtml,
    };
  } catch (err) {
    console.error("Error fetching chapter:", err);
    return null;
  }
}

async function getChapterSeoData(bookIdentifier: string, chapterNum: string) {
  if (isNewBookIdentifier(bookIdentifier)) {
    const publicId = getNewBookPublicId(bookIdentifier);
    if (!publicId) return null;

    const books = await queryD1<D1BookRow>(
      "SELECT id, public_id, title, cover_url, chapter_count FROM books WHERE public_id = ? LIMIT 1",
      [publicId],
      CHAPTER_PAGE_REVALIDATE_SECONDS,
    );
    const book = books[0];
    if (!book) return null;

    const chapters = await queryD1<Pick<D1ChapterRow, "chapter_number" | "title">>(
      "SELECT chapter_number, title FROM chapters WHERE book_id = ? AND chapter_number = ? LIMIT 1",
      [book.id, Number(chapterNum)],
      CHAPTER_PAGE_REVALIDATE_SECONDS,
    );
    const chapter = chapters[0];
    if (!chapter) return null;

    return {
      book: {
        ...book,
        id: book.public_id || `new-${book.id}`,
      } as Book,
      chapter,
    };
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) return null;
  const bookId = await resolveBookId(bookIdentifier);
  if (!bookId) return null;

  try {
    const headers = { apikey: key, Authorization: `Bearer ${key}` };
    const [resBook, resChapter] = await Promise.all([
      fetch(`${url}/rest/v1/books?id=eq.${bookId}&select=id,title,cover_url`, {
        headers,
        next: { revalidate: CHAPTER_PAGE_REVALIDATE_SECONDS },
      }),
      fetch(
        `${url}/rest/v1/chapters?book_id=eq.${bookId}&chapter_number=eq.${chapterNum}&select=chapter_number,title`,
        {
          headers,
          next: { revalidate: CHAPTER_PAGE_REVALIDATE_SECONDS },
        }
      ),
    ]);

    if (!resBook.ok || !resChapter.ok) return null;
    const books = await resBook.json() as Book[];
    const chapters = await resChapter.json() as Pick<Chapter, "chapter_number" | "title">[];
    if (!books[0] || !chapters[0]) return null;

    return {
      book: books[0],
      chapter: chapters[0],
    };
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { id: string; chapterNum: string };
}): Promise<Metadata> {
  const data = await getChapterSeoData(params.id, params.chapterNum);
  if (!data) {
    return {
      title: "Không tìm thấy chương",
    };
  }

  const { book, chapter } = data;
  const siteUrl = getSiteUrl();
  const path = getChapterPath(book, chapter.chapter_number);
  const cleanChapterTitle = getCleanChapterTitle(chapter.title, chapter.chapter_number);
  const title = `${book.title} - Chương ${chapter.chapter_number}: ${cleanChapterTitle}`;
  const description = buildChapterDescription(book.title, chapter.title, chapter.chapter_number);
  const images = book.cover_url ? [{ url: book.cover_url, alt: book.title }] : undefined;

  return {
    title,
    description,
    alternates: {
      canonical: `${siteUrl}${path}`,
    },
    openGraph: {
      type: "article",
      siteName: SITE_NAME,
      title,
      description,
      url: `${siteUrl}${path}`,
      images,
      locale: "vi_VN",
    },
    twitter: {
      card: book.cover_url ? "summary_large_image" : "summary",
      title,
      description,
      images: book.cover_url ? [book.cover_url] : undefined,
    },
  };
}

export default async function ChapterPage({
  params,
}: {
  params: { id: string; chapterNum: string };
}) {
  const data = await getChapterData(params.id, params.chapterNum);

  if (!data) {
    notFound();
  }

  const { book, chapter, contentHtml } = data;
  const currentNum = parseInt(params.chapterNum, 10);

  const prevNum = currentNum > 1 ? currentNum - 1 : null;
  const nextNum = currentNum < (book.chapter_count || 9999) ? currentNum + 1 : currentNum + 1;

  return (
    <ChapterReader
      bookId={book.id}
      bookTitle={book.title}
      chapterNumber={chapter.chapter_number}
      chapterTitle={chapter.title}
      contentHtml={contentHtml}
      prevNum={prevNum}
      nextNum={nextNum}
      chapterCount={book.chapter_count || 0}
    />
  );
}
