import BookCard from "@/components/BookCard";

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
    title: "Độc Tôn Truyền Kỳ (Kiếm Thần Yêu Nghiệt)",
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
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
      },
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
        status: b.status || ("Đang ra" as const),
        coverUrl: b.cover_url || "https://images.unsplash.com/photo-1541963463532-d68292c34b19?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
      }))
    : MOCK_BOOKS;

  return (
    <div className="flex flex-col gap-6">
      {/* Dynamic Book Grid Header */}
      <div className="flex items-center justify-between border-b border-[#C69C4E]/30 pb-3">
        <h1 className="text-xl font-bold flex items-center gap-2.5 text-[#2C2825]">
          <span className="w-1.5 h-6 bg-[#C69C4E] inline-block rounded-full"></span>
          Danh Sách Truyện ({booksToDisplay.length})
        </h1>
      </div>
      
      {/* Book Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-x-5 gap-y-7">
        {booksToDisplay.map((book) => (
          <BookCard key={book.id} {...book} />
        ))}
      </div>
    </div>
  );
}
