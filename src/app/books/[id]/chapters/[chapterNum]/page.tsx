import Link from 'next/link';
import { notFound } from 'next/navigation';

export const revalidate = 0;

interface Chapter {
  id: number;
  book_id: number;
  chapter_number: number;
  title: string;
  content_html: string;
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
    const resBook = await fetch(`${url}/rest/v1/books?id=eq.${bookId}`, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
      cache: 'no-store',
    });
    if (!resBook.ok) return null;
    const books = await resBook.json();
    if (!books || books.length === 0) return null;

    const resChapter = await fetch(
      `${url}/rest/v1/chapters?book_id=eq.${bookId}&chapter_number=eq.${chapterNum}`,
      {
        headers: { apikey: key, Authorization: `Bearer ${key}` },
        cache: 'no-store',
      }
    );
    if (!resChapter.ok) return null;
    const chapters = await resChapter.json();
    if (!chapters || chapters.length === 0) return null;

    return {
      book: books[0] as Book,
      chapter: chapters[0] as Chapter,
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

  const { book, chapter } = data;
  const currentNum = parseInt(params.chapterNum, 10);

  const prevNum = currentNum > 1 ? currentNum - 1 : null;
  const nextNum = currentNum + 1; // Allows navigating to next chapter

  return (
    <div className="max-w-3xl mx-auto py-6 flex flex-col gap-6">
      {/* Navigation Breadcrumb */}
      <div className="flex justify-between items-center text-sm text-gray-500 border-b pb-3">
        <Link href={`/books/${book.id}`} className="hover:text-blue-600 font-medium">
          &larr; {book.title}
        </Link>
        <span className="font-semibold text-gray-700">Chương {chapter.chapter_number}</span>
      </div>

      {/* Chapter Title */}
      <div className="text-center my-4">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 leading-snug">{chapter.title}</h1>
      </div>

      {/* Chapter Reader Controls Top */}
      <div className="flex justify-between items-center py-2 px-4 bg-gray-50 rounded-lg text-sm font-medium">
        {prevNum ? (
          <Link
            href={`/books/${book.id}/chapters/${prevNum}`}
            className="text-blue-600 hover:underline"
          >
            &larr; Chương trước
          </Link>
        ) : (
          <span className="text-gray-400">&larr; Chương trước</span>
        )}

        <Link href={`/books/${book.id}`} className="text-gray-600 hover:text-blue-600">
          Mục lục
        </Link>

        <Link
          href={`/books/${book.id}/chapters/${nextNum}`}
          className="text-blue-600 hover:underline"
        >
          Chương sau &rarr;
        </Link>
      </div>

      {/* Main Chapter Content */}
      <div
        className="prose prose-lg max-w-none text-gray-800 leading-relaxed font-serif bg-white p-6 md:p-10 rounded-xl shadow-sm border border-gray-100 whitespace-pre-wrap"
        dangerouslySetInnerHTML={{ __html: chapter.content_html }}
      />

      {/* Chapter Reader Controls Bottom */}
      <div className="flex justify-between items-center py-3 px-4 bg-gray-50 rounded-lg text-sm font-medium mt-4">
        {prevNum ? (
          <Link
            href={`/books/${book.id}/chapters/${prevNum}`}
            className="text-blue-600 hover:underline"
          >
            &larr; Chương trước
          </Link>
        ) : (
          <span className="text-gray-400">&larr; Chương trước</span>
        )}

        <Link href={`/books/${book.id}`} className="text-gray-600 hover:text-blue-600">
          Mục lục
        </Link>

        <Link
          href={`/books/${book.id}/chapters/${nextNum}`}
          className="text-blue-600 hover:underline"
        >
          Chương sau &rarr;
        </Link>
      </div>
    </div>
  );
}
