"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

interface BookComment {
  id: number;
  book_id: number;
  chapter_number?: number | null;
  nickname: string;
  content: string;
  rating?: number | null;
  created_at: string;
}

interface BookCommentsProps {
  bookId: number;
  chapterNumber?: number;
  showList?: boolean;
  compact?: boolean;
}

const COMMENT_COOLDOWN_KEY = "tien-hiep-lau:comment-last-sent";
const CLIENT_COOLDOWN_MS = 2 * 60 * 1000;

function formatCommentTime(value: string) {
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return "";
  }
}

function getClientCooldownRemaining(bookId: number) {
  try {
    const raw = window.localStorage.getItem(COMMENT_COOLDOWN_KEY);
    const sentMap = raw ? JSON.parse(raw) : {};
    const lastSentAt = Number(sentMap?.[bookId] || 0);
    return Math.max(0, CLIENT_COOLDOWN_MS - (Date.now() - lastSentAt));
  } catch {
    return 0;
  }
}

function setClientCooldown(bookId: number) {
  try {
    const raw = window.localStorage.getItem(COMMENT_COOLDOWN_KEY);
    const sentMap = raw ? JSON.parse(raw) : {};
    window.localStorage.setItem(
      COMMENT_COOLDOWN_KEY,
      JSON.stringify({ ...sentMap, [bookId]: Date.now() })
    );
  } catch {
    // Server-side cooldown still protects the endpoint.
  }
}

export default function BookComments({
  bookId,
  chapterNumber,
  showList = true,
  compact = false,
}: BookCommentsProps) {
  const [comments, setComments] = useState<BookComment[]>([]);
  const [loading, setLoading] = useState(showList);
  const [nickname, setNickname] = useState("");
  const [content, setContent] = useState("");
  const [rating, setRating] = useState("5");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const averageRating = useMemo(() => {
    const ratings = comments
      .map((comment) => comment.rating)
      .filter((value): value is number => Number.isInteger(value));

    if (ratings.length === 0) return null;
    const total = ratings.reduce((sum, value) => sum + value, 0);
    return (total / ratings.length).toFixed(1);
  }, [comments]);

  const loadComments = async () => {
    if (!showList) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/books/${bookId}/comments`, {
        cache: "no-store",
      });
      const data = await response.json() as { comments?: BookComment[] };
      setComments(data.comments || []);
    } catch {
      setComments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadComments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId, showList]);

  const submitComment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage("");
    setError("");

    const remaining = getClientCooldownRemaining(bookId);
    if (remaining > 0) {
      setError(`Bạn vừa gửi bình luận. Vui lòng thử lại sau khoảng ${Math.ceil(remaining / 1000)} giây.`);
      return;
    }

    const cleanedNickname = nickname.trim();
    const cleanedContent = content.trim();
    if (cleanedNickname.length < 2) {
      setError("Nick name cần ít nhất 2 ký tự.");
      return;
    }
    if (cleanedContent.length < 3) {
      setError("Bình luận cần ít nhất 3 ký tự.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch(`/api/books/${bookId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nickname: cleanedNickname,
          content: cleanedContent,
          rating: Number(rating),
          chapterNumber: chapterNumber || null,
        }),
      });
      const data = await response.json() as { comment?: BookComment; error?: string };

      if (!response.ok) {
        setError(data.error || "Không thể gửi bình luận lúc này.");
        return;
      }

      setClientCooldown(bookId);
      setContent("");
      setMessage(showList ? "Đã gửi bình luận." : "Đã gửi bình luận cho truyện này.");
      if (showList && data.comment) {
        setComments((current) => [data.comment as BookComment, ...current].slice(0, 60));
      }
    } catch {
      setError("Không thể gửi bình luận lúc này.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className={`rounded-lg border border-[#DDD5C8] bg-[#FBFAF7]/92 shadow-[0_8px_24px_rgba(66,52,35,0.06)] ${compact ? "p-4" : "p-5 md:p-6"}`}>
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-serif-reading text-xl font-bold text-[#2C2825]">
            Bình luận
          </h2>
          {showList && (
            <p className="mt-1 text-xs text-[#8C8373]">
              {comments.length}/60 bình luận{averageRating ? ` · Đánh giá ${averageRating}/5` : ""}
            </p>
          )}
        </div>
        {chapterNumber && (
          <span className="text-xs font-semibold text-[#8C8373]">
            Từ chương {chapterNumber}
          </span>
        )}
      </div>

      <form onSubmit={submitComment} className="flex flex-col gap-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_112px]">
          <input
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            maxLength={40}
            placeholder="Nick name"
            className="w-full rounded-md border border-[#D8CDBB] bg-white/90 px-3 py-2 text-sm text-[#2C2825] outline-none transition-colors placeholder:text-[#9A9182] focus:border-[#B99654]"
          />
          <select
            value={rating}
            onChange={(event) => setRating(event.target.value)}
            className="w-full rounded-md border border-[#D8CDBB] bg-white/90 px-3 py-2 text-sm font-semibold text-[#2C2825] outline-none transition-colors focus:border-[#B99654]"
          >
            <option value="5">5 sao</option>
            <option value="4">4 sao</option>
            <option value="3">3 sao</option>
            <option value="2">2 sao</option>
            <option value="1">1 sao</option>
          </select>
        </div>

        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          maxLength={1000}
          rows={compact ? 3 : 4}
          placeholder="Viết cảm nhận của bạn"
          className="w-full resize-y rounded-md border border-[#D8CDBB] bg-white/90 px-3 py-2 text-sm leading-6 text-[#2C2825] outline-none transition-colors placeholder:text-[#9A9182] focus:border-[#B99654]"
        />

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <span className="text-xs text-[#8C8373]">
            {content.length}/1000
          </span>
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center justify-center rounded-md bg-[#2C2825] px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#4A443A] disabled:cursor-wait disabled:opacity-65"
          >
            {submitting ? "Đang gửi..." : "Gửi bình luận"}
          </button>
        </div>

        {(message || error) && (
          <p className={`text-sm font-medium ${error ? "text-[#A04A3A]" : "text-[#557A36]"}`}>
            {error || message}
          </p>
        )}
      </form>

      {showList && (
        <div className="mt-6 border-t border-[#E8E0D2] pt-4">
          {loading ? (
            <p className="py-4 text-center text-sm text-[#8C8373]">Đang tải bình luận...</p>
          ) : comments.length === 0 ? (
            <p className="py-4 text-center text-sm text-[#8C8373]">
              Chưa có bình luận nào.
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {comments.map((comment) => (
                <article
                  key={comment.id}
                  className="rounded-md border border-[#E8E0D2] bg-white/70 p-3"
                >
                  <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                    <strong className="text-sm text-[#2C2825]">{comment.nickname}</strong>
                    {comment.rating && (
                      <span className="font-semibold text-[#A37B34]">{comment.rating}/5 sao</span>
                    )}
                    {comment.chapter_number && (
                      <span className="text-[#8C8373]">Chương {comment.chapter_number}</span>
                    )}
                    <time className="text-[#8C8373]">{formatCommentTime(comment.created_at)}</time>
                  </div>
                  <p className="whitespace-pre-wrap break-words text-sm leading-6 text-[#4A443A]">
                    {comment.content}
                  </p>
                </article>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
