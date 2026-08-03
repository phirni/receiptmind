import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Search as SearchIcon, ArrowRight } from "lucide-react";
import clsx from "clsx";
import { api, ApiError } from "../api/client.js";
import { Spinner, EmptyState } from "../components/Status.jsx";
import { formatCurrency, formatDate } from "../lib/format.js";
import { useToast } from "../components/Toast.jsx";

const MODES = [
  { value: "hybrid", label: "Hybrid" },
  { value: "semantic", label: "Semantic" },
  { value: "keyword", label: "Keyword" },
];

const EXAMPLES = ["coffee", "vegetables", "things I bought at the airport", "snacks", "protein"];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [merchant, setMerchant] = useState("");
  const toast = useToast();

  const runSearch = async (q = query) => {
    if (!q.trim()) return;
    setQuery(q);
    setLoading(true);
    try {
      const res = await api.search({ query: q, mode, merchant: merchant || undefined, limit: 20 });
      setResults(res);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-ash-100">Search your receipts</h1>
        <p className="mt-1 text-sm text-ash-500">
          Search by meaning, not just exact words — "coffee" also finds lattes, espresso, and cold brew.
        </p>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          runSearch();
        }}
        className="flex items-center gap-2"
      >
        <div className="relative flex-1">
          <SearchIcon size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ash-700" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Try 'coffee' or 'things I bought at the airport'"
            className="focus-ring w-full rounded-lg border border-line bg-surface py-2.5 pl-10 pr-3 text-sm text-ash-100 placeholder:text-ash-700"
          />
        </div>
        <button
          type="submit"
          className="focus-ring rounded-lg bg-amber px-4 py-2.5 font-display text-sm font-semibold text-ink hover:opacity-90"
        >
          Search
        </button>
      </form>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => setMode(m.value)}
            className={clsx(
              "focus-ring rounded-full border px-3 py-1 text-xs",
              mode === m.value ? "border-amber text-amber" : "border-line text-ash-500 hover:text-ash-100"
            )}
          >
            {m.label}
          </button>
        ))}
        <span className="mx-1 h-3 w-px bg-line" />
        <input
          value={merchant}
          onChange={(e) => setMerchant(e.target.value)}
          placeholder="Filter merchant"
          className="focus-ring w-32 rounded-full border border-line bg-surface px-3 py-1 text-xs text-ash-100 placeholder:text-ash-700"
        />
      </div>

      {!results && !loading && (
        <div className="mt-6 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => runSearch(ex)}
              className="focus-ring rounded-full border border-line px-3 py-1 text-xs text-ash-500 hover:border-teal-soft hover:text-ash-100"
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      {loading && <Spinner label="Searching…" />}

      {!loading && results && results.results.length === 0 && (
        <EmptyState title="No matches" hint="Try a broader search term, or switch modes." icon={SearchIcon} />
      )}

      {!loading && results && results.results.length > 0 && (
        <div className="mt-8 space-y-3">
          {results.results.map((r) => (
            <Link
              key={r.receipt_id}
              to={`/receipts/${r.receipt_id}`}
              className="focus-ring block rounded-lg border border-line bg-surface p-4 transition-colors hover:border-teal-soft"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-display text-sm font-medium text-ash-100">{r.merchant_name}</p>
                  <p className="text-xs text-ash-500">{formatDate(r.purchase_datetime)}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="stat-figure text-sm text-ash-100">{formatCurrency(r.total, r.currency)}</span>
                  <ArrowRight size={14} className="text-ash-700" />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {r.matched_items.map((m) => (
                  <span
                    key={m.line_item_id}
                    className="rounded bg-teal-dim px-2 py-0.5 text-xs text-teal-soft"
                    title={`match score ${m.score}`}
                  >
                    {m.name}
                  </span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
