import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pagination({ page, pages, onChange }) {
  if (pages <= 1) return null;
  return (
    <div className="flex items-center justify-center gap-3 pt-6">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="focus-ring flex h-8 w-8 items-center justify-center rounded-md border border-line text-ash-300 hover:text-amber disabled:opacity-30 disabled:hover:text-ash-300"
      >
        <ChevronLeft size={15} />
      </button>
      <span className="stat-figure text-xs text-ash-500">
        {page} / {pages}
      </span>
      <button
        onClick={() => onChange(page + 1)}
        disabled={page >= pages}
        className="focus-ring flex h-8 w-8 items-center justify-center rounded-md border border-line text-ash-300 hover:text-amber disabled:opacity-30 disabled:hover:text-ash-300"
      >
        <ChevronRight size={15} />
      </button>
    </div>
  );
}
