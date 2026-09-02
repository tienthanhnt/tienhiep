import { Suspense } from "react";
import BookSearchSection from "@/components/BookSearchSection";
import RecentReading from "@/components/RecentReading";
import AdsterraBanner4 from "@/components/AdsterraBanner4";
import { queryD1 } from "@/lib/d1";
import { formatCompactNumber } from "@/lib/format";
import { getSiteUrl, SITE_NAME } from "@/lib/seo";
import { redirect } from "next/navigation";

export const revalidate = 1800;
const BOOKS_PER_PAGE = 20;
const SITE_DESCRIPTION = "Đọc truyện tiên hiệp, huyền huyễn, kiếm hiệp và tu tiên dịch full tiếng Việt miễn phí, cập nhật chương mới mỗi ngày.";
const DEFAULT_COVER_URL = "https://images.unsplash.com/photo-1541963463532-d68292c34b19?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80";

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
  id: number | string;
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

interface D1Book {
  id: number;
  public_id?: string | null;
  title: string;
  author: string;
  chapter_count: number;
  rating: number;
  status: 'Đang ra' | 'Hoàn thành';
  cover_url: string;
  genres?: string | null;
  source_type?: string | null;
  ranking?: number | null;
}

function mapBook(b: SupabaseBook): BookItem {
  return {
    id: b.id,
    title: b.title,
    author: b.author || "Chưa rõ",
    chapterCount: b.chapter_count || 0,
    rating: b.rating || 8.0,
    status: (b.status || "Đang ra") as 'Đang ra' | 'Hoàn thành',
    coverUrl: b.cover_url || DEFAULT_COVER_URL,
    genres: b.genres || "",
    sourceType: b.source_type || "",
    viewCount: b.view_count || 0,
    ranking: b.ranking ?? null,
  };
}

function mapD1Book(b: D1Book): BookItem {
  return {
    id: b.public_id || `new-${b.id}`,
    title: b.title,
    author: b.author || "Chưa rõ",
    chapterCount: b.chapter_count || 0,
    rating: b.rating || 8.0,
    status: (b.status || "Đang ra") as 'Đang ra' | 'Hoàn thành',
    coverUrl: b.cover_url || DEFAULT_COVER_URL,
    genres: b.genres || "",
    sourceType: b.source_type || "",
    viewCount: 0,
    ranking: b.ranking ?? null,
  };
}

function sortBooks(a: BookItem, b: BookItem) {
  const rankA = a.ranking ?? Number.POSITIVE_INFINITY;
  const rankB = b.ranking ?? Number.POSITIVE_INFINITY;
  if (rankA !== rankB) return rankA - rankB;
  return String(a.id).localeCompare(String(b.id), "vi");
}

async function getSupabaseBooks() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return [];

  try {
    const res = await fetch(`${url}/rest/v1/books?select=id,title,author,chapter_count,rating,status,cover_url,genres,source_type,view_count,ranking&order=ranking.asc.nullslast,id.asc`, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
      },
      next: { revalidate: 1800 },
    });
    if (!res.ok) return [];
    return await res.json() as SupabaseBook[];
  } catch {
    return [];
  }
}

async function getD1Books() {
  return queryD1<D1Book>(
    `
    SELECT id, public_id, title, author, chapter_count, rating, status,
           cover_url, genres, source_type, ranking
    FROM books
    ORDER BY ranking ASC, id ASC
    `,
    [],
    1800,
  );
}

export default async function Home({
  searchParams,
}: {
  searchParams?: { page?: string };
}) {
  const requestedPage = Math.max(1, Number(searchParams?.page || "1") || 1);
  const [supabaseBooks, d1Books] = await Promise.all([
    getSupabaseBooks(),
    getD1Books(),
  ]);

  const searchBooks = [...supabaseBooks.map(mapBook), ...d1Books.map(mapD1Book)].sort(sortBooks);
  const totalCount = searchBooks.length;
  const offset = (requestedPage - 1) * BOOKS_PER_PAGE;
  const books = searchBooks.slice(offset, offset + BOOKS_PER_PAGE);
  const totalViewCount = searchBooks.reduce((sum, book) => sum + (book.viewCount || 0), 0);
  const totalPages = Math.max(1, Math.ceil(totalCount / BOOKS_PER_PAGE));

  if (totalCount > 0 && requestedPage > totalPages) {
    redirect(totalPages === 1 ? "/" : `/?page=${totalPages}`);
  }

  const siteUrl = getSiteUrl();
  const websiteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: siteUrl,
    inLanguage: "vi",
    description: SITE_DESCRIPTION,
  };
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: SITE_NAME,
    url: siteUrl,
    inLanguage: "vi",
    description: "Danh sách truyện tiên hiệp, huyền huyễn, kiếm hiệp và tu tiên tiếng Việt.",
    numberOfItems: totalCount,
  };

  return (
    <div className="flex flex-col gap-3 md:gap-4">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify([websiteJsonLd, collectionJsonLd]).replace(/</g, "\\u003c"),
        }}
      />

      <section className="text-center pt-1 pb-3 md:pb-4 border-b border-[#DDD5C8]/80">
        <div className="mx-auto mb-2 h-px w-28 soft-divider" />
        <h1 className="font-serif-reading text-3xl md:text-5xl font-bold text-[#26211C] leading-tight">
          Tiên Hiệp Lâu
        </h1>
        <p className="mt-2 text-sm md:text-base text-[#5E5448] font-serif-reading italic leading-relaxed">
          &ldquo;Độc vạn quyển thư, hành vạn lý lộ, phá vạn trùng quan.&rdquo;
        </p>
        <p className="mx-auto mt-2 max-w-2xl text-xs md:text-sm leading-6 text-[#6B6357]">
          {SITE_DESCRIPTION}
        </p>
        <div className="mx-auto mt-3 h-px w-20 soft-divider opacity-70" />
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
          totalCount={totalCount}
          pageSize={BOOKS_PER_PAGE}
        />
      </Suspense>

      {/* Bottom ad section: Medium Rectangle */}
      <div className="flex flex-col items-center gap-4 my-4 w-full overflow-hidden">
        <div className="flex justify-center w-full">
          <AdsterraBanner4 />
        </div>
      </div>

      <div className="self-center rounded border border-[#E8E0D2] px-2.5 py-1 text-[11px] text-[#A09688]">
        Tổng lượt đọc: {formatCompactNumber(totalViewCount)}
      </div>

    </div>
  );
}
