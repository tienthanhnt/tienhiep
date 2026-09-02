import type { MetadataRoute } from "next";
import { queryD1 } from "@/lib/d1";
import { getBookPath, getSiteUrl } from "@/lib/seo";

export const revalidate = 3600;

interface SitemapBook {
  id: number | string;
  title: string;
  created_at?: string | null;
}

interface D1SitemapBook {
  id: number;
  public_id?: string | null;
  title: string;
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
  const [supabaseBooks, d1Books] = await Promise.all([
    fetchAllFromSupabase<SitemapBook>("books?select=id,title,created_at&order=ranking.asc.nullslast,id.asc"),
    queryD1<D1SitemapBook>(
      "SELECT id, public_id, title, created_at FROM books ORDER BY ranking ASC, id ASC",
      [],
      3600,
    ),
  ]);
  const books: SitemapBook[] = [
    ...supabaseBooks,
    ...d1Books.map((book) => ({
      id: book.public_id || `new-${book.id}`,
      title: book.title,
      created_at: book.created_at,
    })),
  ];

  return [
    {
      url: siteUrl,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    ...books.map((book) => ({
      url: `${siteUrl}${getBookPath(book)}`,
      lastModified: book.created_at ? new Date(book.created_at) : new Date(),
      changeFrequency: "daily" as const,
      priority: 0.8,
    })),
  ];
}
