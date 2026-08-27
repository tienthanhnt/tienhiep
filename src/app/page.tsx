import { Suspense } from "react";
import BookSearchSection from "@/components/BookSearchSection";
import RecentReading from "@/components/RecentReading";
import AdsterraBanner3 from "@/components/AdsterraBanner3";
import AdsterraBanner4 from "@/components/AdsterraBanner4";
import { formatCompactNumber } from "@/lib/format";
import { redirect } from "next/navigation";

export const revalidate = 1800;
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
    viewCount: 0,
    ranking: null,
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
    viewCount: 0,
    ranking: null,
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
  view_count?: number | null;
  ranking?: number | null;
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
  viewCount: number;
  ranking: number | null;
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
    viewCount: b.view_count || 0,
    ranking: b.ranking ?? null,
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
    const res = await fetch(`${url}/rest/v1/books?select=*&order=ranking.asc.nullslast,id.asc&limit=${BOOKS_PER_PAGE}&offset=${offset}`, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        Prefer: "count=exact",
      },
      next: { revalidate: 1800 },
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
    const res = await fetch(`${url}/rest/v1/books?select=id,title,author,chapter_count,rating,status,cover_url,genres,source_type,view_count,ranking&order=ranking.asc.nullslast,id.asc`, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
      next: { revalidate: 1800 },
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
  const totalViewCount = searchBooks.reduce((sum, book) => sum + (book.viewCount || 0), 0);
  const totalPages = Math.max(1, Math.ceil((totalCount || books.length) / BOOKS_PER_PAGE));

  if (totalCount > 0 && requestedPage > totalPages) {
    redirect(totalPages === 1 ? "/" : `/?page=${totalPages}`);
  }

  return (
    <div className="flex flex-col gap-5 md:gap-6">
      <section className="text-center pt-1 pb-5 md:pb-6 border-b border-[#DDD5C8]/80">
        <div className="mx-auto mb-3 h-px w-28 soft-divider" />
        <h1 className="font-serif-reading text-3xl md:text-5xl font-bold text-[#26211C] leading-tight">
          Tiên Hiệp Lâu
        </h1>
        <p className="mt-2 text-sm md:text-base text-[#5E5448] font-serif-reading italic leading-relaxed">
          &ldquo;Độc vạn quyển thư, hành vạn lý lộ, phá vạn trùng quan.&rdquo;
        </p>
        <div className="mx-auto mt-4 h-px w-20 soft-divider opacity-70" />
      </section>

      <RecentReading />

      <Suspense fallback={
        <div className="rounded-md border border-[#DDD5C8] bg-[#FBFAF7] px-4 py-8 text-center text-sm text-[#6B6357]">
          Đang tải danh sách truyện...
        </div>
      }>
        <BookSearchSection
          books={books}
          searchBooks={searchBooks}
          currentPage={requestedPage}
          totalPages={totalPages}
          totalCount={totalCount || books.length}
          pageSize={BOOKS_PER_PAGE}
        />
      </Suspense>

      {/* Bottom ad section: Medium Rectangle + Leaderboard */}
      <div className="flex flex-col items-center gap-4 my-4 w-full overflow-hidden">
        <div className="flex justify-center w-full">
          <AdsterraBanner4 />
        </div>
        <div className="flex justify-center w-full hidden md:flex">
          <AdsterraBanner3 />
        </div>
      </div>

      <div className="self-center rounded border border-[#E8E0D2] px-2.5 py-1 text-[11px] text-[#A09688]">
        Tổng lượt đọc: {formatCompactNumber(totalViewCount)}
      </div>

    </div>
  );
}
