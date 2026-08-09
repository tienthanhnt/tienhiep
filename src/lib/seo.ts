export const SITE_NAME = "Tiên Hiệp Lâu";

export function getSiteUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_SITE_URL || process.env.VERCEL_URL;
  if (!configuredUrl) return "http://localhost:3000";

  const siteUrl = configuredUrl.startsWith("http") ? configuredUrl : `https://${configuredUrl}`;
  return siteUrl.replace(/\/+$/, "");
}

export function buildBookDescription(book: {
  title: string;
  author?: string | null;
  status?: string | null;
  chapter_count?: number | null;
}) {
  const author = book.author || "Chưa rõ";
  const status = book.status || "Đang ra";
  const chapterCount = book.chapter_count || 0;

  return `Đọc truyện ${book.title} của tác giả ${author} tại ${SITE_NAME}. Truyện ${status.toLowerCase()}, hiện có ${chapterCount} chương, giao diện đọc gọn nhẹ và dễ theo dõi.`;
}

export function getCleanChapterTitle(chapterTitle: string, chapterNumber: number) {
  return chapterTitle.replace(new RegExp(`^\\s*Chương\\s+${chapterNumber}\\s*[:.-]?\\s*`, "i"), "").trim() || chapterTitle;
}

export function buildChapterDescription(bookTitle: string, chapterTitle: string, chapterNumber: number) {
  const cleanChapterTitle = getCleanChapterTitle(chapterTitle, chapterNumber);
  return `Đọc ${bookTitle} - Chương ${chapterNumber}: ${cleanChapterTitle} tại ${SITE_NAME}. Nội dung chương được trình bày gọn nhẹ, dễ đọc trên điện thoại và máy tính.`;
}
