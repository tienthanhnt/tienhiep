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
      {/* Back button */}
      <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-[#8C8373] hover:text-[#A37B34] font-medium w-fit">
        &larr; Trở về Trang Chủ
      </Link>

      {/* Book Info Header */}
      <div className="ancient-card p-6 md:p-8 rounded-2xl flex flex-col md:flex-row gap-8 border border-[#C69C4E]/30">
        <img
          src={book.cover_url || "https://images.unsplash.com/photo-1541963463532-d68292c34b19"}
          alt={book.title}
          className="w-48 h-68 object-cover rounded-xl shadow-lg border border-[#C69C4E]/40 self-center md:self-start shrink-0"
        />
        <div className="flex flex-col justify-between flex-1 gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-[#2C2825] mb-3 leading-snug">{book.title}</h1>
            <p className="text-[#6B6357] text-sm mb-4">Tác giả: <span className="font-semibold text-[#2C2825]">{book.author || "Chưa rõ"}</span></p>
            
            <div className="flex flex-wrap gap-2.5 text-xs font-semibold">
              <span className="bg-[#181D27] text-[#D4AF37] px-3 py-1.5 rounded-md border border-[#C69C4E]/30">
                {book.status || "Đang ra"}
              </span>
              <span className="bg-[#EFE9DC] text-[#7A5B1E] px-3 py-1.5 rounded-md border border-[#C69C4E]/30">
                ⭐ {book.rating ? Number(book.rating).toFixed(1) : "8.0"} / 10
              </span>
              <span className="bg-[#EFE9DC] text-[#4A443A] px-3 py-1.5 rounded-md border border-[#C69C4E]/30">
                📜 {chapters.length} chương
              </span>
            </div>
          </div>

          {chapters.length > 0 && (
            <Link
              href={`/books/${book.id}/chapters/${chapters[0].chapter_number}`}
              className="inline-flex items-center justify-center bg-gradient-to-r from-[#A37B34] to-[#C69C4E] hover:from-[#8C6627] hover:to-[#A37B34] text-white font-bold px-7 py-3 rounded-xl shadow-md transition-all w-fit gap-2"
            >
              <span>📖</span> Đọc từ chương 1
            </Link>
          )}
        </div>
      </div>

      {/* Chapters Table */}
      <div className="ancient-card p-6 md:p-8 rounded-2xl border border-[#C69C4E]/30">
        <h2 className="text-xl font-bold text-[#2C2825] mb-5 border-b border-[#C69C4E]/20 pb-3 flex items-center gap-2">
          <span>📚</span> Mục Lục Chương ({chapters.length})
        </h2>

        {chapters.length === 0 ? (
          <p className="text-[#8C8373] py-6 text-center text-sm">Chưa có chương nào được upload.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {chapters.map((ch) => (
              <Link
                key={ch.id}
                href={`/books/${book.id}/chapters/${ch.chapter_number}`}
                className="p-3.5 rounded-xl bg-white/60 hover:bg-[#EFE9DC] text-[#2C2825] hover:text-[#A37B34] text-sm font-medium transition-all flex justify-between items-center border border-[#E8E0D2] hover:border-[#C69C4E]/40"
              >
                <span className="truncate">{ch.title}</span>
                <span className="text-xs text-[#8C8373] shrink-0 ml-3 bg-[#E8E0D2]/60 px-2 py-0.5 rounded">
                  Chương {ch.chapter_number}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
