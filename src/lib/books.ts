import { slugifyVietnamese } from "./seo";

interface BookSlugItem {
  id: number;
  title: string;
}

const BOOK_SLUG_CACHE_SECONDS = 3600;

export async function resolveBookId(identifier: string) {
  if (/^\d+$/.test(identifier)) return identifier;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;

  try {
    const response = await fetch(
      `${url}/rest/v1/books?select=id,title&order=ranking.asc.nullslast,id.asc`,
      {
        headers: {
          apikey: key,
          Authorization: `Bearer ${key}`,
        },
        next: { revalidate: BOOK_SLUG_CACHE_SECONDS },
      }
    );

    if (!response.ok) return null;
    const books = await response.json() as BookSlugItem[];
    const matchedBook = books.find((book) => slugifyVietnamese(book.title) === identifier);
    return matchedBook ? String(matchedBook.id) : null;
  } catch {
    return null;
  }
}
