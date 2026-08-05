export default function ChapterLoading() {
  return (
    <div className="max-w-3xl mx-auto py-4 flex flex-col gap-6 animate-pulse">
      <div className="flex justify-between items-center border-b border-[#C69C4E]/20 pb-3">
        <div className="h-4 w-40 rounded bg-[#D8CFBE]" />
        <div className="h-7 w-24 rounded-full bg-[#E8E0D2]" />
      </div>

      <div className="h-14 rounded-xl bg-[#181D27]/90 border border-[#C69C4E]/20" />

      <div className="flex justify-between items-center">
        <div className="h-9 w-32 rounded-lg bg-[#EFE9DC] border border-[#C69C4E]/20" />
        <div className="h-4 w-20 rounded bg-[#D8CFBE]" />
        <div className="h-9 w-32 rounded-lg bg-[#EFE9DC] border border-[#C69C4E]/20" />
      </div>

      <div className="p-6 md:p-12 rounded-2xl border border-[#C69C4E]/30 bg-[#F4EFE6] shadow-sm">
        <div className="mx-auto mb-8 h-8 w-64 rounded bg-[#D8CFBE]" />
        <div className="border-t border-[#C69C4E]/20 pt-8 space-y-4">
          <div className="h-5 w-full rounded bg-[#DED5C5]" />
          <div className="h-5 w-11/12 rounded bg-[#DED5C5]" />
          <div className="h-5 w-full rounded bg-[#DED5C5]" />
          <div className="h-5 w-10/12 rounded bg-[#DED5C5]" />
          <div className="h-5 w-full rounded bg-[#DED5C5]" />
          <div className="h-5 w-8/12 rounded bg-[#DED5C5]" />
        </div>
      </div>
    </div>
  );
}
