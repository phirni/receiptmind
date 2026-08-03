import React from "react";
import { Loader2, Inbox } from "lucide-react";

export function Spinner({ label }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-ash-500">
      <Loader2 size={18} className="animate-spin" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}

export function EmptyState({ title, hint, icon: Icon = Inbox }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-line py-16 text-center">
      <Icon size={22} className="text-ash-700" />
      <p className="font-display text-sm font-medium text-ash-300">{title}</p>
      {hint && <p className="max-w-xs text-xs text-ash-500">{hint}</p>}
    </div>
  );
}
