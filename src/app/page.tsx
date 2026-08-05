import BookCard from "@/components/BookCard";

export const revalidate = 0;

const MOCK_BOOKS = [
  {
    id: 101,
    title: "Tuyệt Thế Dược Thần",
    author: "Hoa Tiên Tửu",
    chapterCount: 4993,
    rating: 7.9,
    status: "Đang ra" as const,
    coverUrl: "https://images.unsplash.com/photo-1541963463532-d68292c34b19?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
  },
  {
    id: 102,
    title: "Độc Tôn Truyền Kỳ",
    author: "Lâm Nhất",
    chapterCount: 7077,
    rating: 7.9,
    status: "Đang ra" as const,
    coverUrl: "https://images.unsplash.com/photo-1618666012174-83b441c0bc76?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
  },
];

interface SupabaseBook {
  id: number;
  title: string;
  author: string;
  chapter_count: number;
  rating: number;
  status: 'Đang ra' | 'Hoàn thành';
  cover_url: string;
}

async function getBooks() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return [];
  try {
    const res = await fetch(`${url}/rest/v1/books?select=*&order=created_at.desc`, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
      cache: 'no-store',
    });
    if (!res.ok) return [];
    return await res.json() as SupabaseBook[];
  } catch { return []; }
}

export default async function Home() {
  const dbBooks = await getBooks();

  const books = dbBooks.length > 0
    ? dbBooks.map((b) => ({
        id: b.id,
        title: b.title,
        author: b.author || "Chưa rõ",
        chapterCount: b.chapter_count || 0,
        rating: b.rating || 8.0,
        status: (b.status || "Đang ra") as 'Đang ra' | 'Hoàn thành',
        coverUrl: b.cover_url || MOCK_BOOKS[0].coverUrl,
      }))
    : MOCK_BOOKS;

  return (
    <div className="flex flex-col gap-7">
      <section className="border-b border-[#DDD5C8] pb-6">
        <h1 className="text-2xl md:text-3xl font-bold text-[#26211C] leading-tight">
          Tàng Kinh Các
        </h1>
        <p className="mt-2 text-sm md:text-base text-[#6F675D]">
          Thư viện truyện gọn nhẹ, tập trung vào trải nghiệm đọc.
        </p>
      </section>

      <section>
        <div className="flex items-center gap-3 mb-5">
          <h2 className="text-base font-bold text-[#26211C]">
            Danh sách truyện
          </h2>
          <span className="text-xs text-[#8C8373]">({books.length} bộ)</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-5 md:gap-6">
          {books.map((book) => (
            <BookCard key={book.id} {...book} />
          ))}
        </div>
      </section>

    </div>
  );
}
