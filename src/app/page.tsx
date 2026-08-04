import BookCard from "@/components/BookCard";
import AdSlot from "@/components/AdSlot";

export const revalidate = 0;

const MOCK_BOOKS = [
  {
    id: 101,
    title: "Tuyệt Thế Dược Thần - Diệp Viễn",
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
    const data: SupabaseBook[] = await res.json();
    return data;
  } catch (err) {
    console.error("Lỗi khi kết nối Supabase:", err);
    return [];
  }
}

export default async function Home() {
  const dbBooks = await getBooks();

  const booksToDisplay = dbBooks.length > 0
    ? dbBooks.map((b) => ({
        id: b.id,
        title: b.title,
        author: b.author || "Chưa rõ",
        chapterCount: b.chapter_count || 0,
        rating: b.rating || 8.0,
        status: (b.status || "Đang ra") as 'Đang ra' | 'Hoàn thành',
        coverUrl: b.cover_url || "https://images.unsplash.com/photo-1541963463532-d68292c34b19?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
      }))
    : MOCK_BOOKS;

  return (
    <div className="flex flex-col gap-5">
      {/* === Top Banner Ad === */}
      <AdSlot type="banner" label="Quảng Cáo Banner Trên Cùng · 728×90" />

      {/* === Main Content + Sidebar === */}
      <div className="flex gap-6 items-start">

        {/* ── Left: Main book grid ── */}
        <div className="flex-1 min-w-0 flex flex-col gap-5">

          {/* Header */}
          <div className="flex items-center justify-between border-b border-[#C69C4E]/30 pb-3">
            <h1 className="text-lg font-bold flex items-center gap-2 text-[#2C2825]">
              <span className="w-1 h-5 bg-[#C69C4E] inline-block rounded-full"></span>
              Danh Sách Truyện
              <span className="text-sm font-normal text-[#9C8E7E]">({booksToDisplay.length})</span>
            </h1>
          </div>

          {/* Book Grid — 4 columns on desktop */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 md:gap-5">
            {booksToDisplay.map((book) => (
              <BookCard key={book.id} {...book} />
            ))}
          </div>

          {/* Inline Ad between rows */}
          <AdSlot type="inline" label="Quảng Cáo Nội Dung" />

        </div>

        {/* ── Right: Sidebar with Ads ── */}
        <aside className="hidden lg:flex flex-col gap-4 w-[240px] shrink-0 sticky top-20">
          <div className="text-[10px] text-[#A89C7E] font-semibold tracking-widest uppercase px-1">Tài Trợ</div>
          <AdSlot type="sidebar" label="Quảng Cáo Sidebar" />
          <AdSlot type="sidebar" label="Quảng Cáo Sidebar 2" />
        </aside>

      </div>
    </div>
  );
}
