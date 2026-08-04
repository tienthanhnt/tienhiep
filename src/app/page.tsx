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
    <div className="flex flex-col gap-10">
      {/* Banner Phong Cách Cổ Giấy / Tiên Hiệp */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#1E2533] via-[#181D27] to-[#2A2118] text-[#E5DDCB] p-8 md:p-10 border border-[#C69C4E]/40 shadow-xl">
        <div className="absolute top-0 right-0 w-64 h-64 bg-[#C69C4E]/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#C69C4E]/15 border border-[#C69C4E]/30 text-[#D4AF37] text-xs font-semibold mb-4">
            <span>⛩️ Thư Viện Tiên Hiệp</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-wide mb-3 font-cinzel text-white leading-tight">
            Thế Giới Tu Tiên Kỳ Ảo
          </h1>
          <p className="text-sm md:text-base text-[#B8AE9C] leading-relaxed max-w-2xl font-serif-reading">
            Đắm chìm vào những pho bí kíp tu tiên, vượt qua tam tai cửu kiếp, lĩnh hội thiên đạo trường sinh. Tất cả tác phẩm đều được trau chuốt văn phong thuần Việt mượt mà.
          </p>
        </div>
      </section>

      {/* Danh sách Truyện Mới Cập Nhật */}
      <section>
        <div className="flex items-center justify-between mb-6 border-b border-[#C69C4E]/30 pb-3">
          <h2 className="text-xl font-bold flex items-center gap-2.5 text-[#2C2825]">
            <span className="w-1.5 h-6 bg-[#C69C4E] inline-block rounded-full"></span>
            Tiểu Thuyết Mới Cập Nhật
          </h2>
          <span className="text-xs text-[#A37B34] font-semibold tracking-wide">TỔNG HỢP TIÊN HIỆP</span>
        </div>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-5 gap-y-8">
          {booksToDisplay.map((book) => (
            <BookCard key={book.id} {...book} />
          ))}
        </div>
      </section>

      {/* Giới thiệu Đọc Truyện */}
      <section className="ancient-card p-6 md:p-8 rounded-xl border border-[#C69C4E]/30 mt-4">
        <h2 className="text-lg font-bold mb-3 text-[#2C2825] flex items-center gap-2">
          <span>📜</span> Không Gian Đọc Truyện Chuẩn Văn Phong
        </h2>
        <p className="text-sm text-[#5C5449] leading-relaxed mb-3 font-serif-reading">
          Tàng Kinh Các là nơi lưu giữ những bản dịch tiểu thuyết Tiên Hiệp được biên tập kỹ lưỡng. Từng câu chữ được gọt giũa thuần Việt, giữ nguyên tinh thần võ học và thần thoại phương Đông.
        </p>
      </section>
    </div>
  );
}
