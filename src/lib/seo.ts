export const SITE_NAME = "Tiên Hiệp Lâu";

export function getSiteUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_SITE_URL || process.env.VERCEL_URL;
  if (!configuredUrl) return "http://localhost:3000";

  const siteUrl = configuredUrl.startsWith("http") ? configuredUrl : `https://${configuredUrl}`;
  return siteUrl.replace(/\/+$/, "");
}

export function slugifyVietnamese(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function getBookPath(book: { id: number | string; title: string }) {
  const slug = slugifyVietnamese(book.title);
  return `/books/${slug ? `${book.id}-${slug}` : book.id}`;
}

export function getChapterPath(book: { id: number | string; title: string }, chapterNumber: number) {
  return `${getBookPath(book)}/chapters/${chapterNumber}`;
}

export function buildBookDescription(book: {
  title: string;
  author?: string | null;
  status?: string | null;
  chapter_count?: number | null;
  description?: string | null;
  genres?: string | null;
  source_type?: string | null;
}) {
  if (book.description?.trim()) {
    return book.description.trim();
  }

  const author = book.author || "Chưa rõ";
  const status = book.status || "Đang ra";
  const chapterCount = book.chapter_count || 0;
  const genres = book.genres ? ` Thể loại: ${book.genres}.` : "";
  const sourceType = book.source_type ? ` Bản ${book.source_type.toLowerCase()}.` : "";

  return `Đọc truyện ${book.title} của tác giả ${author} tại ${SITE_NAME}. Truyện ${status.toLowerCase()}, hiện có ${chapterCount} chương.${genres}${sourceType} Giao diện đọc gọn nhẹ và dễ theo dõi.`;
}

export function getCleanChapterTitle(chapterTitle: string, chapterNumber: number) {
  return chapterTitle.replace(new RegExp(`^\\s*Chương\\s+${chapterNumber}\\s*[:.-]?\\s*`, "i"), "").trim() || chapterTitle;
}

export function buildChapterDescription(bookTitle: string, chapterTitle: string, chapterNumber: number) {
  const cleanChapterTitle = getCleanChapterTitle(chapterTitle, chapterNumber);
  return `Đọc ${bookTitle} - Chương ${chapterNumber}: ${cleanChapterTitle} tại ${SITE_NAME}. Nội dung chương được trình bày gọn nhẹ, dễ đọc trên điện thoại và máy tính.`;
}
