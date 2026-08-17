export function formatCompactNumber(value?: number | null) {
  const number = value || 0;
  return new Intl.NumberFormat("vi-VN", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(number);
}

