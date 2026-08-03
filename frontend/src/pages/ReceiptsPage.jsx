import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpDown, Trash2, Search as SearchIcon } from "lucide-react";
import { api, ApiError } from "../api/client.js";
import { Spinner, EmptyState } from "../components/Status.jsx";
import Pagination from "../components/Pagination.jsx";
import { formatCurrency, formatDate } from "../lib/format.js";
import { useToast } from "../components/Toast.jsx";

const SORT_OPTIONS = [
  { value: "created_at", label: "Date added" },
  { value: "purchase_datetime", label: "Purchase date" },
  { value: "total", label: "Total" },
  { value: "merchant_name", label: "Merchant" },
];

export default function ReceiptsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [merchant, setMerchant] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");
  const toast = useToast();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .listReceipts({
        page,
        page_size: 15,
        merchant: merchant || undefined,
        min_price: minPrice || undefined,
        max_price: maxPrice || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
      })
      .then((res) => !cancelled && setData(res))
      .catch((err) => !cancelled && toast.error(err instanceof ApiError ? err.message : "Failed to load receipts."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [page, merchant, minPrice, maxPrice, sortBy, sortDir, toast]);

  const toggleSort = (field) => {
    if (sortBy === field) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
    setPage(1);
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this receipt? This can't be undone.")) return;
    try {
      await api.deleteReceipt(id);
      toast.success("Receipt deleted.");
      setData((d) => (d ? { ...d, items: d.items.filter((r) => r.id !== id) } : d));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete receipt.");
    }
  };

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ash-100">Receipts</h1>
          <p className="mt-1 text-sm text-ash-500">{data ? `${data.total} total` : "\u00A0"}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <SearchIcon size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ash-700" />
            <input
              value={merchant}
              onChange={(e) => {
                setMerchant(e.target.value);
                setPage(1);
              }}
              placeholder="Filter by merchant"
              className="focus-ring w-44 rounded-md border border-line bg-surface py-1.5 pl-7 pr-2 text-xs text-ash-100 placeholder:text-ash-700"
            />
          </div>
          <input
            value={minPrice}
            onChange={(e) => {
              setMinPrice(e.target.value);
              setPage(1);
            }}
            type="number"
            placeholder="Min $"
            className="focus-ring w-20 rounded-md border border-line bg-surface px-2 py-1.5 text-xs text-ash-100 placeholder:text-ash-700"
          />
          <input
            value={maxPrice}
            onChange={(e) => {
              setMaxPrice(e.target.value);
              setPage(1);
            }}
            type="number"
            placeholder="Max $"
            className="focus-ring w-20 rounded-md border border-line bg-surface px-2 py-1.5 text-xs text-ash-100 placeholder:text-ash-700"
          />
          <select
            value={sortBy}
            onChange={(e) => toggleSort(e.target.value)}
            className="focus-ring rounded-md border border-line bg-surface px-2 py-1.5 text-xs text-ash-100"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                Sort: {o.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      {loading && <Spinner label="Loading receipts…" />}

      {!loading && data && data.items.length === 0 && (
        <EmptyState title="No receipts yet" hint="Upload a receipt to see it appear here." />
      )}

      {!loading && data && data.items.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-line">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-surface text-left text-xs uppercase tracking-wide text-ash-500">
                <Th label="Merchant" field="merchant_name" active={sortBy} onClick={toggleSort} />
                <Th label="Date" field="purchase_datetime" active={sortBy} onClick={toggleSort} />
                <th className="px-4 py-2.5 font-medium">Items</th>
                <Th label="Total" field="total" active={sortBy} onClick={toggleSort} align="right" />
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {data.items.map((r) => (
                <tr key={r.id} className="border-b border-line/60 last:border-0 hover:bg-raised/50">
                  <td className="px-4 py-3">
                    <Link to={`/receipts/${r.id}`} className="focus-ring rounded font-medium text-ash-100 hover:text-amber">
                      {r.merchant_name}
                    </Link>
                    {r.status !== "processed" && (
                      <span className="ml-2 rounded bg-danger/20 px-1.5 py-0.5 text-[10px] uppercase text-danger">
                        {r.status}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-ash-500">{formatDate(r.purchase_datetime)}</td>
                  <td className="px-4 py-3 text-ash-500">{r.item_count}</td>
                  <td className="stat-figure px-4 py-3 text-right text-ash-100">{formatCurrency(r.total, r.currency)}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleDelete(r.id)} className="focus-ring text-ash-700 hover:text-danger">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && <Pagination page={data.page} pages={data.pages} onChange={setPage} />}
    </div>
  );
}

function Th({ label, field, active, onClick, align = "left" }) {
  return (
    <th className={`px-4 py-2.5 font-medium ${align === "right" ? "text-right" : "text-left"}`}>
      <button
        onClick={() => onClick(field)}
        className={`focus-ring inline-flex items-center gap-1 rounded ${active === field ? "text-amber" : ""}`}
      >
        {label}
        <ArrowUpDown size={11} />
      </button>
    </th>
  );
}
