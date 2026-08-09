import type { MetadataRoute } from "next";
import { getSiteUrl } from "@/lib/seo";

export const revalidate = 3600;

interface SitemapBook {
  id: number;
  created_at?: string | null;
}

interface SitemapChapter {
  book_id: number;
  chapter_number: number;
  created_at?: string | null;
}

async function fetchAllFromSupabase<T>(path: string) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return [];

  const rows: T[] = [];
  const pageSize = 1000;
  const headers = { apikey: key, Authorization: `Bearer ${key}` };

  for (let from = 0; ; from += pageSize) {
    const to = from + pageSize - 1;
    try {
      const response = await fetch(`${url}/rest/v1/${path}`, {
        headers: {
          ...headers,
          Range: `${from}-${to}`,
        },
        next: { revalidate: 3600 },
      });

      if (!response.ok) break;
      const batch = await response.json() as T[];
      rows.push(...batch);
      if (batch.length < pageSize) break;
    } catch {
      break;
    }
  }

  return rows;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl = getSiteUrl();
  const [books, chapters] = await Promise.all([
    fetchAllFromSupabase<SitemapBook>("books?select=id,created_at&order=created_at.desc"),
    fetchAllFromSupabase<SitemapChapter>("chapters?select=book_id,chapter_number,created_at&order=book_id.asc,chapter_number.asc"),
  ]);

  return [
    {
      url: siteUrl,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    ...books.map((book) => ({
      url: `${siteUrl}/books/${book.id}`,
      lastModified: book.created_at ? new Date(book.created_at) : new Date(),
      changeFrequency: "daily" as const,
      priority: 0.8,
    })),
    ...chapters.map((chapter) => ({
      url: `${siteUrl}/books/${chapter.book_id}/chapters/${chapter.chapter_number}`,
      lastModified: chapter.created_at ? new Date(chapter.created_at) : new Date(),
      changeFrequency: "weekly" as const,
      priority: 0.6,
    })),
  ];
}
