"use client";

import { FormEvent, useMemo, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import BookCard from "@/components/BookCard";

interface BookSearchItem {
  id: number | string;
  title: string;
  author: string;
  chapterCount: number;
  rating: number;
  status: "Đang ra" | "Hoàn thành";
  coverUrl: string;
  genres?: string;
  sourceType?: string;
}

interface BookSearchSectionProps {
  books: BookSearchItem[];
  searchBooks: BookSearchItem[];
  currentPage: number;
  totalPages: number;
  totalCount: number;
  pageSize: number;
}

function normalizeSearchText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .trim();
}

function getSearchContent(book: BookSearchItem) {
  return normalizeSearchText([
    book.title,
    book.author,
    book.genres,
    book.sourceType,
    book.status,
  ].filter(Boolean).join(" "));
}

function getPageNumbers(currentPage: number, totalPages: number) {
  const pages = new Set([1, totalPages, currentPage - 1, currentPage, currentPage + 1]);
  return Array.from(pages)
    .filter((page) => page >= 1 && page <= totalPages)
    .sort((a, b) => a - b);
}

function pageHref(page: number) {
  return page <= 1 ? "/" : `/?page=${page}`;
}

export default function BookSearchSection({
  books,
  searchBooks,
  currentPage,
  totalPages,
  totalCount,
  pageSize,
}: BookSearchSectionProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlQuery = searchParams.get("q") || "";

  const [inputValue, setInputValue] = useState(urlQuery);
  const [query, setQuery] = useState(urlQuery);

  useEffect(() => {
    setInputValue(urlQuery);
    setQuery(urlQuery);
  }, [urlQuery]);

  const searchableBooks = useMemo(
    () => searchBooks.map((book) => ({ book, searchContent: getSearchContent(book) })),
    [searchBooks]
  );

  const normalizedQuery = normalizeSearchText(query);
  const filteredBooks = normalizedQuery
    ? searchableBooks
        .filter(({ searchContent }) => searchContent.includes(normalizedQuery))
        .map(({ book }) => book)
    : books;
  const isSearching = Boolean(normalizedQuery);
  const pageNumbers = getPageNumbers(currentPage, totalPages);
  const firstVisible = totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const lastVisible = Math.min(currentPage * pageSize, totalCount);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(inputValue);
    if (inputValue.trim()) {
      router.push(`/?q=${encodeURIComponent(inputValue.trim())}`);
    } else {
      router.push("/");
    }
  }

  function clearSearch() {
    setInputValue("");
    setQuery("");
    router.push("/");
  }

  return (
    <section>
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="flex items-center gap-3 border-l-2 border-[#B99654] pl-3">
          <h2 className="text-base font-bold text-[#26211C] tracking-wide">
            Danh sách truyện
          </h2>
          <span className="text-xs text-[#8C8373]">
            {isSearching
              ? `(${filteredBooks.length}/${searchBooks.length} bộ)`
              : `(${firstVisible}-${lastVisible}/${totalCount} bộ)`}
          </span>
        </div>

        <form onSubmit={handleSubmit} className="flex w-full gap-2 md:max-w-md">
          <input
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            type="search"
            placeholder="Tìm tên truyện, tác giả, thể loại"
            className="h-10 min-w-0 flex-1 rounded-md border border-[#D8CDBB] bg-[#FBFAF7] px-3 text-sm text-[#2C2825] outline-none transition focus:border-[#B99654] focus:ring-2 focus:ring-[#B99654]/20"
          />
          <button
            type="submit"
            className="h-10 shrink-0 rounded-md bg-[#2C2825] px-4 text-sm font-semibold text-white transition hover:bg-[#4A443A] focus:outline-none focus:ring-2 focus:ring-[#B99654]/40"
          >
            Tìm kiếm
          </button>
        </form>
      </div>

      {normalizedQuery && (
        <div className="mb-5 flex items-center justify-between gap-3 rounded-md border border-[#DDD5C8] bg-[#FBFAF7] px-3 py-2 text-sm text-[#6B6357]">
          <span className="truncate">
            Kết quả cho: <span className="font-semibold text-[#2C2825]">{query}</span>
          </span>
          <button
            type="button"
            onClick={clearSearch}
            className="shrink-0 text-xs font-semibold text-[#8A6828] hover:text-[#5E461A]"
          >
            Xóa
          </button>
        </div>
      )}

      {filteredBooks.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-5 md:gap-6">
          {filteredBooks.map((book) => (
            <BookCard key={book.id} {...book} />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-[#DDD5C8] bg-[#FBFAF7] px-4 py-8 text-center text-sm text-[#6B6357]">
          Không tìm thấy truyện phù hợp.
        </div>
      )}

      {!isSearching && totalPages > 1 && (
        <nav className="mt-8 flex flex-wrap items-center justify-center gap-2" aria-label="Phân trang truyện">
          {currentPage > 1 && (
            <Link
              href={pageHref(currentPage - 1)}
              className="inline-flex h-9 items-center rounded-md border border-[#D8CDBB] bg-[#FBFAF7] px-3 text-sm font-semibold text-[#5C5449] transition hover:border-[#B99654] hover:text-[#7A5B1E]"
            >
              Trước
            </Link>
          )}

          {pageNumbers.map((page, index) => {
            const previousPage = pageNumbers[index - 1];
            const showGap = previousPage && page - previousPage > 1;

            return (
              <span key={page} className="flex items-center gap-2">
                {showGap && <span className="text-sm text-[#8C8373]">...</span>}
                <Link
                  href={pageHref(page)}
                  aria-current={page === currentPage ? "page" : undefined}
                  className={`inline-flex h-9 min-w-9 items-center justify-center rounded-md border px-3 text-sm font-semibold transition ${
                    page === currentPage
                      ? "border-[#2C2825] bg-[#2C2825] text-white"
                      : "border-[#D8CDBB] bg-[#FBFAF7] text-[#5C5449] hover:border-[#B99654] hover:text-[#7A5B1E]"
                  }`}
                >
                  {page}
                </Link>
              </span>
            );
          })}

          {currentPage < totalPages && (
            <Link
              href={pageHref(currentPage + 1)}
              className="inline-flex h-9 items-center rounded-md border border-[#D8CDBB] bg-[#FBFAF7] px-3 text-sm font-semibold text-[#5C5449] transition hover:border-[#B99654] hover:text-[#7A5B1E]"
            >
              Sau
            </Link>
          )}
        </nav>
      )}
    </section>
  );
}
