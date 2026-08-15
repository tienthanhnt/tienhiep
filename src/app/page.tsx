import BookSearchSection from "@/components/BookSearchSection";
import RecentReading from "@/components/RecentReading";
import { redirect } from "next/navigation";

export const revalidate = 600;
const BOOKS_PER_PAGE = 20;

const MOCK_BOOKS = [
  {
    id: 101,
    title: "Tuyệt Thế Dược Thần",
    author: "Hoa Tiên Tửu",
    chapterCount: 4993,
    rating: 7.9,
    status: "Đang ra" as const,
    coverUrl: "https://images.unsplash.com/photo-1541963463532-d68292c34b19?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80",
    genres: "",
    sourceType: "",
  },
  {
    id: 102,
    title: "Độc Tôn Truyền Kỳ",
    author: "Lâm Nhất",
    chapterCount: 7077,
    rating: 7.9,
    status: "Đang ra" as const,
    coverUrl: "https://images.unsplash.com/photo-1618666012174-83b441c0bc76?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80",
    genres: "",
    sourceType: "",
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
  genres?: string | null;
  source_type?: string | null;
}

interface BookItem {
  id: number;
  title: string;
  author: string;
  chapterCount: number;
  rating: number;
  status: 'Đang ra' | 'Hoàn thành';
  coverUrl: string;
  genres: string;
  sourceType: string;
}

function mapBook(b: SupabaseBook): BookItem {
  return {
    id: b.id,
    title: b.title,
    author: b.author || "Chưa rõ",
    chapterCount: b.chapter_count || 0,
    rating: b.rating || 8.0,
    status: (b.status || "Đang ra") as 'Đang ra' | 'Hoàn thành',
    coverUrl: b.cover_url || MOCK_BOOKS[0].coverUrl,
    genres: b.genres || "",
    sourceType: b.source_type || "",
  };
}

function parseTotalCount(contentRange: string | null) {
  if (!contentRange) return 0;
  const match = contentRange.match(/\/(\d+)$/);
  return match ? Number(match[1]) : 0;
}

async function getBooksPage(page: number) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return { books: [] as SupabaseBook[], totalCount: 0 };

  const offset = (page - 1) * BOOKS_PER_PAGE;
  try {
    const res = await fetch(`${url}/rest/v1/books?select=*&order=id.asc&limit=${BOOKS_PER_PAGE}&offset=${offset}`, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        Prefer: "count=exact",
      },
      next: { revalidate: 600 },
    });
    if (!res.ok) return { books: [] as SupabaseBook[], totalCount: 0 };
    return {
      books: await res.json() as SupabaseBook[],
      totalCount: parseTotalCount(res.headers.get("content-range")),
    };
  } catch {
    return { books: [] as SupabaseBook[], totalCount: 0 };
  }
}

async function getSearchBooks() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return [];

  try {
    const res = await fetch(`${url}/rest/v1/books?select=id,title,author,chapter_count,rating,status,cover_url,genres,source_type&order=id.asc`, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
      next: { revalidate: 600 },
    });
    if (!res.ok) return [];
    return await res.json() as SupabaseBook[];
  } catch {
    return [];
  }
}

export default async function Home({
  searchParams,
}: {
  searchParams?: { page?: string };
}) {
  const requestedPage = Math.max(1, Number(searchParams?.page || "1") || 1);
  const [{ books: dbBooks, totalCount }, searchDbBooks] = await Promise.all([
    getBooksPage(requestedPage),
    getSearchBooks(),
  ]);

  const books = dbBooks.length > 0
    ? dbBooks.map(mapBook)
    : MOCK_BOOKS;
  const searchBooks = searchDbBooks.length > 0 ? searchDbBooks.map(mapBook) : books;
  const totalPages = Math.max(1, Math.ceil((totalCount || books.length) / BOOKS_PER_PAGE));

  if (totalCount > 0 && requestedPage > totalPages) {
    redirect(totalPages === 1 ? "/" : `/?page=${totalPages}`);
  }

  return (
    <div className="flex flex-col gap-9">
      <section className="text-center pt-2 pb-9 border-b border-[#DDD5C8]/80">
        <div className="mx-auto mb-4 h-px w-32 soft-divider" />
        <h1 className="font-serif-reading text-3xl md:text-5xl font-bold text-[#26211C] leading-tight">
          Tiên Hiệp Lâu
        </h1>
        <p className="mt-3 text-sm md:text-base text-[#5E5448] font-serif-reading italic leading-relaxed">
          &ldquo;Độc vạn quyển thư, hành vạn lý lộ, phá vạn trùng quan.&rdquo;
        </p>
        <div className="mx-auto mt-5 h-px w-24 soft-divider opacity-70" />
      </section>

      <RecentReading />

      <BookSearchSection
        books={books}
        searchBooks={searchBooks}
        currentPage={requestedPage}
        totalPages={totalPages}
        totalCount={totalCount || books.length}
        pageSize={BOOKS_PER_PAGE}
      />

    </div>
  );
}
