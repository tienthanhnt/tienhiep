import Link from 'next/link';
import { notFound } from 'next/navigation';

export const revalidate = 0;

interface Chapter {
  id: number;
  chapter_number: number;
  title: string;
  created_at: string;
}

interface Book {
  id: number;
  title: string;
  author: string;
  cover_url: string;
  status: string;
  rating: number;
  chapter_count: number;
}

async function getBookDetails(id: string) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) return null;

  try {
    const resBook = await fetch(`${url}/rest/v1/books?id=eq.${id}`, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
      cache: 'no-store',
    });
    if (!resBook.ok) return null;
    const books = await resBook.json();
    if (!books || books.length === 0) return null;

    const resChapters = await fetch(
      `${url}/rest/v1/chapters?book_id=eq.${id}&select=id,chapter_number,title,created_at&order=chapter_number.asc`,
      {
        headers: { apikey: key, Authorization: `Bearer ${key}` },
        cache: 'no-store',
      }
    );
    const chapters = resChapters.ok ? await resChapters.json() : [];

    return {
      book: books[0] as Book,
      chapters: chapters as Chapter[],
    };
  } catch (err) {
    console.error("Error fetching book details:", err);
    return null;
  }
}

export default async function BookDetailPage({ params }: { params: { id: string } }) {
  const data = await getBookDetails(params.id);

  if (!data) {
    notFound();
  }

  const { book, chapters } = data;

  return (
    <div className="flex flex-col gap-8 max-w-4xl mx-auto py-4">
      {/* Header / Meta */}
      <div className="flex flex-col md:flex-row gap-6 bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <img
          src={book.cover_url || "https://images.unsplash.com/photo-1541963463532-d68292c34b19"}
          alt={book.title}
          className="w-44 h-64 object-cover rounded-lg shadow-md self-center md:self-start"
        />
        <div className="flex flex-col justify-between flex-1 gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{book.title}</h1>
            <p className="text-gray-600 text-sm mb-4">Tác giả: <span className="font-medium text-gray-800">{book.author || "Chưa rõ"}</span></p>
            <div className="flex gap-3 text-sm">
              <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full font-medium">Trạng thái: {book.status || "Đang ra"}</span>
              <span className="bg-amber-50 text-amber-700 px-3 py-1 rounded-full font-medium">Đánh giá: ⭐ {book.rating || 8.0}</span>
              <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full font-medium">{chapters.length} chương</span>
            </div>
          </div>

          {chapters.length > 0 && (
            <Link
              href={`/books/${book.id}/chapters/${chapters[0].chapter_number}`}
              className="inline-flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-2.5 rounded-lg transition-colors w-fit"
            >
              Đọc từ chương đầu
            </Link>
          )}
        </div>
      </div>

      {/* Danh sách chương */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <h2 className="text-xl font-bold mb-4 border-b pb-2">Danh Sách Chương ({chapters.length})</h2>
        {chapters.length === 0 ? (
          <p className="text-gray-500 py-4 text-center">Chưa có chương nào được upload.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {chapters.map((ch) => (
              <Link
                key={ch.id}
                href={`/books/${book.id}/chapters/${ch.chapter_number}`}
                className="p-3 rounded-lg hover:bg-blue-50 text-gray-700 hover:text-blue-700 text-sm font-medium transition-colors flex justify-between items-center border border-gray-50"
              >
                <span className="truncate">{ch.title}</span>
                <span className="text-xs text-gray-400 shrink-0 ml-2">Chương {ch.chapter_number}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
