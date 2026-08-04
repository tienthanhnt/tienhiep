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
    <div className="flex flex-col gap-10">

      {/* ══ Hero: Bồng Lai Tiên Cảnh ══ */}
      <section className="relative flex flex-col items-center text-center pt-8 pb-10 overflow-hidden">
        {/* Layered mist glow behind text */}
        <div className="absolute inset-0 -z-10 pointer-events-none">
          <div className="absolute left-1/2 -translate-x-1/2 top-4 w-[600px] h-[160px] rounded-full bg-[#C69C4E]/8 blur-3xl" />
          <div className="absolute left-1/2 -translate-x-1/2 top-0 w-[300px] h-[80px] rounded-full bg-white/60 blur-2xl" />
        </div>

        {/* Top ornament */}
        <div className="flex items-center gap-4 mb-6">
          <div className="h-px w-20 bg-gradient-to-r from-transparent to-[#C69C4E]/60" />
          <span className="text-[#C69C4E]/70 text-lg select-none">✦</span>
          <span className="text-[#C69C4E]/40 text-xs tracking-[0.4em] font-cinzel uppercase">Bồng Lai Tiên Cảnh</span>
          <span className="text-[#C69C4E]/70 text-lg select-none">✦</span>
          <div className="h-px w-20 bg-gradient-to-l from-transparent to-[#C69C4E]/60" />
        </div>

        {/* Title */}
        <h1 className="font-cinzel font-bold text-4xl md:text-5xl text-[#1E1A16] tracking-wide leading-tight drop-shadow-sm">
          Tàng Kinh Các
        </h1>
        <p className="mt-3 text-[#5E5448] font-serif-reading italic text-sm md:text-base">
          &ldquo;Độc vạn quyển thư, hành vạn lý lộ, phá vạn trùng quan.&rdquo;
        </p>

        {/* Bottom ornament */}
        <div className="flex items-center gap-4 mt-6">
          <div className="h-px w-20 bg-gradient-to-r from-transparent to-[#C69C4E]/60" />
          <span className="text-[#C69C4E]/70 text-lg select-none">✦</span>
          <div className="h-px w-20 bg-gradient-to-l from-transparent to-[#C69C4E]/60" />
        </div>
      </section>

      {/* ══ Book Grid ══ */}
      <section>
        {/* Section header */}
        <div className="flex items-center gap-4 mb-6">
          <div className="h-5 w-0.5 bg-[#C69C4E] rounded-full" />
          <h2 className="text-base font-bold text-[#1E1A16] tracking-wide">
            Mục Lục Tàng Thư
          </h2>
          <span className="text-xs text-[#9A8C78] font-medium">({books.length} bộ)</span>
          <div className="flex-1 h-px bg-gradient-to-r from-[#C69C4E]/30 to-transparent" />
        </div>

        {/* Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-5 md:gap-6">
          {books.map((book) => (
            <BookCard key={book.id} {...book} />
          ))}
        </div>
      </section>

    </div>
  );
}
