import BookCard from "@/components/BookCard";

// Mock data for Tien Hiep stories inspired by MTruyen
const MOCK_BOOKS = [
  {
    id: 1,
    title: "Tuyệt Thế Dược Thần - Diệp Viễn",
    author: "Hoa Tiên Tửu",
    chapterCount: 4993,
    rating: 7.9,
    status: "Đang ra" as const,
    coverUrl: "https://images.unsplash.com/photo-1541963463532-d68292c34b19?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
  },
  {
    id: 2,
    title: "Độc Tôn Truyền Kỳ (Kiếm Thần Yêu Nghiệt)",
    author: "Lâm Nhất",
    chapterCount: 7077,
    rating: 7.9,
    status: "Đang ra" as const,
    coverUrl: "https://images.unsplash.com/photo-1618666012174-83b441c0bc76?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
  },
  {
    id: 3,
    title: "Cực Phẩm Tu Tiên - Kiếm Đạo Đệ Nhất Tiên",
    author: "Bất Tử",
    chapterCount: 111,
    rating: 7.9,
    status: "Đang ra" as const,
    coverUrl: "https://images.unsplash.com/photo-1535905557558-afc4877a26fc?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
  },
  {
    id: 4,
    title: "Tu La Kiếm Thần",
    author: "Tiểu Sơn Trúc",
    chapterCount: 20,
    rating: 7.9,
    status: "Đang ra" as const,
    coverUrl: "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
  },
  {
    id: 5,
    title: "Cải Thiên Nghịch Đạo",
    author: "KK Cố Hương",
    chapterCount: 1850,
    rating: 8.5,
    status: "Hoàn thành" as const,
    coverUrl: "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
  },
];

export default function Home() {
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
        
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-7 xl:grid-cols-8 gap-x-3 gap-y-6">
          {MOCK_BOOKS.map((book) => (
            <BookCard key={book.id} {...book} />
          ))}
        </div>
      </section>

      {/* SEO Section (Giống Mtruyen) */}
      <section className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 mt-4">
        <h2 className="text-lg font-bold mb-3 text-gray-800">Tiên Hiệp - Thể loại dẫn đầu xu hướng</h2>
        <p className="text-sm text-gray-600 leading-relaxed mb-3">
          <strong>Tiên Hiệp</strong> là thể loại truyện xoay quanh quá trình tu luyện, tìm kiếm sự trường sinh và sức mạnh vượt qua giới hạn của phàm nhân. Các nhân vật thường phải trải qua nhiều khó khăn, rèn luyện thân thể và tinh thần, thu thập kỳ trân dị thảo, và chiến đấu với yêu thú hoặc các thế lực tông môn đồ sộ.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          Năm 2026, sự kết hợp giữa Tiên Hiệp và <em>Hệ Thống</em> (LitRPG) tạo ra công thức dẫn đầu về lượng người đọc mới, mang lại nhịp độ dồn dập, cơ chế thăng cấp trực quan và cảm giác sảng khoái (sảng văn). Hãy khám phá kho tàng truyện tu tiên vô tận tại TiênHiệp.net ngay hôm nay!
        </p>
      </section>
    </div>
  );
}
