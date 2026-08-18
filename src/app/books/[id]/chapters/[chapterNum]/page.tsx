import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import ChapterReader from '@/components/ChapterReader';
import { gunzipSync } from 'zlib';
import { buildChapterDescription, getCleanChapterTitle, getSiteUrl, SITE_NAME } from '@/lib/seo';

const CHAPTER_PAGE_REVALIDATE_SECONDS = 86400;
const CHAPTER_CONTENT_REVALIDATE_SECONDS = 604800;

export const revalidate = CHAPTER_PAGE_REVALIDATE_SECONDS;
export const runtime = 'nodejs';

interface Chapter {
  id: number;
  book_id: number;
  chapter_number: number;
  title: string;
  content_html?: string | null;
  content_url?: string | null;
  content_path?: string | null;
}

interface Book {
  id: number;
  title: string;
  chapter_count: number;
  cover_url?: string | null;
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

async function getChapterData(bookId: string, chapterNum: string) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) return null;

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

async function getChapterSeoData(bookId: string, chapterNum: string) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) return null;

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
  const path = `/books/${book.id}/chapters/${chapter.chapter_number}`;
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
