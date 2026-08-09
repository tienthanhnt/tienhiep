import Link from 'next/link';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import ChapterList from '@/components/ChapterList';
import { buildBookDescription, getSiteUrl, SITE_NAME } from '@/lib/seo';

export const revalidate = 900;

interface Chapter {
  id: number;
  chapter_number: number;
  title: string;
  created_at: string;
}

interface Book {
  id: number;
  title: string;
  author: string;
  cover_url: string;
  status: string;
  chapter_count: number;
}

async function getBookDetails(id: string) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) return null;

  try {
    const headers = { apikey: key, Authorization: `Bearer ${key}` };
    const resBook = await fetch(`${url}/rest/v1/books?id=eq.${id}`, {
      headers,
      next: { revalidate: 900 },
    });
    if (!resBook.ok) return null;
    const books = await resBook.json();
    if (!books || books.length === 0) return null;

    const chapters: Chapter[] = [];
    const pageSize = 1000;
    for (let from = 0; ; from += pageSize) {
      const to = from + pageSize - 1;
      const resChapters = await fetch(
        `${url}/rest/v1/chapters?book_id=eq.${id}&select=id,chapter_number,title,created_at&order=chapter_number.asc`,
        {
          headers: {
            ...headers,
            Range: `${from}-${to}`,
          },
          next: { revalidate: 900 },
        }
      );
      if (!resChapters.ok) break;
      const batch = await resChapters.json() as Chapter[];
      chapters.push(...batch);
      if (batch.length < pageSize) break;
    }

    return {
      book: books[0] as Book,
      chapters,
    };
  } catch (err) {
    console.error("Error fetching book details:", err);
    return null;
  }
}

async function getBookSeoData(id: string) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) return null;

  try {
    const res = await fetch(
      `${url}/rest/v1/books?id=eq.${id}&select=id,title,author,cover_url,status,chapter_count`,
      {
        headers: { apikey: key, Authorization: `Bearer ${key}` },
        next: { revalidate: 900 },
      }
    );
    if (!res.ok) return null;
    const books = await res.json() as Book[];
    return books[0] || null;
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const book = await getBookSeoData(params.id);
  if (!book) {
    return {
      title: "Không tìm thấy truyện",
    };
  }

  const siteUrl = getSiteUrl();
  const path = `/books/${book.id}`;
  const description = buildBookDescription(book);
  const images = book.cover_url ? [{ url: book.cover_url, alt: book.title }] : undefined;

  return {
    title: `${book.title} - ${book.author || "Chưa rõ"}`,
    description,
    alternates: {
      canonical: `${siteUrl}${path}`,
    },
    openGraph: {
      type: "book",
      siteName: SITE_NAME,
      title: `${book.title} - ${book.author || "Chưa rõ"}`,
      description,
      url: `${siteUrl}${path}`,
      images,
      locale: "vi_VN",
    },
    twitter: {
      card: book.cover_url ? "summary_large_image" : "summary",
      title: `${book.title} - ${book.author || "Chưa rõ"}`,
      description,
      images: book.cover_url ? [book.cover_url] : undefined,
    },
  };
}

export default async function BookDetailPage({ params }: { params: { id: string } }) {
  const data = await getBookDetails(params.id);

  if (!data) {
    notFound();
  }

  const { book, chapters } = data;

  return (
    <div className="flex flex-col gap-8 max-w-4xl mx-auto py-4">
      {/* Back button */}
      <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-[#8C8373] hover:text-[#A37B34] font-medium w-fit">
        &larr; Trở về Trang Chủ
      </Link>

      {/* Book Info Header */}
      <div className="p-5 md:p-6 rounded-lg flex flex-col md:flex-row gap-7 border border-[#DDD5C8] bg-[#FBFAF7]/90 shadow-[0_8px_26px_rgba(66,52,35,0.07)]">
        <img
          src={book.cover_url || "https://images.unsplash.com/photo-1541963463532-d68292c34b19"}
          alt={book.title}
          className="w-44 h-64 object-cover rounded-md border border-[#D8CDBB] self-center md:self-start shrink-0 shadow-[0_10px_22px_rgba(66,52,35,0.13)]"
        />
        <div className="flex flex-col justify-between flex-1 gap-4">
          <div>
            <h1 className="font-serif-reading text-2xl md:text-3xl font-bold text-[#2C2825] mb-3 leading-snug">{book.title}</h1>
            <p className="text-[#6B6357] text-sm mb-4">Tác giả: <span className="font-semibold text-[#2C2825]">{book.author || "Chưa rõ"}</span></p>
            
            <div className="flex flex-wrap gap-2.5 text-xs font-semibold">
              <span className="bg-[#F4EFE6] text-[#5C5449] px-3 py-1.5 rounded-md border border-[#DDD5C8]">
                {book.status || "Đang ra"}
              </span>
              <span className="bg-[#F4EFE6] text-[#5C5449] px-3 py-1.5 rounded-md border border-[#DDD5C8]">
                {chapters.length} chương
              </span>
            </div>
          </div>

          {chapters.length > 0 && (
            <Link
              href={`/books/${book.id}/chapters/${chapters[0].chapter_number}`}
              className="inline-flex items-center justify-center bg-[#2C2825] hover:bg-[#4A443A] text-white font-semibold px-6 py-2.5 rounded-md transition-all w-fit shadow-sm hover:shadow-md"
            >
              Đọc từ chương 1
            </Link>
          )}
        </div>
      </div>

      <ChapterList bookId={book.id} chapters={chapters} />
    </div>
  );
}
