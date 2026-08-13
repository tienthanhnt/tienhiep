"use client";

import { FormEvent, useMemo, useState } from "react";
import BookCard from "@/components/BookCard";

interface BookSearchItem {
  id: number;
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

export default function BookSearchSection({ books }: BookSearchSectionProps) {
  const [inputValue, setInputValue] = useState("");
  const [query, setQuery] = useState("");

  const searchableBooks = useMemo(
    () => books.map((book) => ({ book, searchContent: getSearchContent(book) })),
    [books]
  );

  const normalizedQuery = normalizeSearchText(query);
  const filteredBooks = normalizedQuery
    ? searchableBooks
        .filter(({ searchContent }) => searchContent.includes(normalizedQuery))
        .map(({ book }) => book)
    : books;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(inputValue);
  }

  function clearSearch() {
    setInputValue("");
    setQuery("");
  }

  return (
    <section>
      <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex items-center gap-3 border-l-2 border-[#B99654] pl-3">
          <h2 className="text-base font-bold text-[#26211C] tracking-wide">
            Danh sách truyện
          </h2>
          <span className="text-xs text-[#8C8373]">
            ({filteredBooks.length}/{books.length} bộ)
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
    </section>
  );
}
