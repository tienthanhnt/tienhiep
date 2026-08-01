import BookCard from "@/components/BookCard";

export const revalidate = 0; // Disable caching to fetch live data from Supabase

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
      {/* Banner Khuyến Nghị */}
      <section className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-xl p-8 text-white shadow-lg">
        <h1 className="text-3xl font-bold mb-2">Thế Giới Tiên Hiệp Kỳ Ảo</h1>
        <p className="opacity-90 max-w-2xl">
          Đắm chìm vào những câu chuyện tu tiên, luyện đạo, vượt qua tam tai cửu kiếp để đạt được sự trường sinh bất lão. Cập nhật các tiểu thuyết huyền huyễn, tiên hiệp mới nhất và hay nhất.
        </p>
      </section>

      {/* Danh sách Truyện Mới Cập Nhật */}
      <section>
        <div className="flex items-center justify-between mb-6 border-b pb-2 border-gray-200">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <span className="w-1.5 h-6 bg-blue-600 inline-block rounded-sm"></span>
            Tiên Hiệp Mới Cập Nhật
          </h2>
          <a href="#" className="text-sm text-blue-600 hover:underline font-medium">Xem tất cả &rarr;</a>
        </div>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-6 gap-x-4 gap-y-6">
          {booksToDisplay.map((book) => (
            <BookCard key={book.id} {...book} />
          ))}
        </div>
      </section>

      {/* SEO Section */}
      <section className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 mt-4">
        <h2 className="text-lg font-bold mb-3 text-gray-800">Tiên Hiệp - Thể loại dẫn đầu xu hướng</h2>
        <p className="text-sm text-gray-600 leading-relaxed mb-3">
          <strong>Tiên Hiệp</strong> là thể loại truyện xoay quanh quá trình tu luyện, tìm kiếm sự trường sinh và sức mạnh vượt qua giới hạn của phàm nhân. Các nhân vật thường phải trải qua nhiều khó khăn, rèn luyện thân thể và tinh thần, thu thập kỳ trân dị thảo, và chiến đấu với yêu thú hoặc các thế lực tông môn đồ sộ.
        </p>
      </section>
    </div>
  );
}
