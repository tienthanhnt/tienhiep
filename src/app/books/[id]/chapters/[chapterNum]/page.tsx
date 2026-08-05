import { notFound } from 'next/navigation';
import ChapterReader from '@/components/ChapterReader';

export const revalidate = 0;

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
        cache: 'no-store',
      }),
      fetch(
        `${url}/rest/v1/chapters?book_id=eq.${bookId}&chapter_number=eq.${chapterNum}&select=id,book_id,chapter_number,title,content_html,content_url,content_path`,
        {
          headers,
          cache: 'no-store',
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
      const resContent = await fetch(chapter.content_url, {
        next: { revalidate: 3600 },
      });
      if (!resContent.ok) return null;
      contentHtml = await resContent.text();
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
    />
  );
}
