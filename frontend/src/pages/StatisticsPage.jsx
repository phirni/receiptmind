import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, ApiError } from "../api/client.js";
import { Spinner, EmptyState } from "../components/Status.jsx";
import { formatCurrency } from "../lib/format.js";
import { useToast } from "../components/Toast.jsx";

export default function StatisticsPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch((err) => toast.error(err instanceof ApiError ? err.message : "Failed to load statistics."))
      .finally(() => setLoading(false));
  }, [toast]);

  if (loading) return <Spinner label="Crunching numbers…" />;
  if (!stats) return null;
  if (stats.total_receipts === 0) {
    return <EmptyState title="No data yet" hint="Upload some receipts to see spending statistics here." />;
  }

  return (
    <div>
      <header className="mb-8">
        <h1 className="font-display text-2xl font-semibold text-ash-100">Statistics</h1>
        <p className="mt-1 text-sm text-ash-500">An overview of your spending.</p>
      </header>

      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total receipts" value={stats.total_receipts} />
        <StatCard label="Total spent" value={formatCurrency(stats.total_spent)} />
        <StatCard label="Avg. receipt" value={formatCurrency(stats.average_receipt_value)} />
        <StatCard label="Merchants" value={stats.merchant_frequency.length} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <ChartCard title="Monthly spending">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stats.monthly_spending}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A3B36" vertical={false} />
              <XAxis dataKey="month" tick={{ fill: "#7D8985", fontSize: 11 }} axisLine={{ stroke: "#2A3B36" }} tickLine={false} />
              <YAxis tick={{ fill: "#7D8985", fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
              <Tooltip
                contentStyle={{ background: "#1B2925", border: "1px solid #2A3B36", borderRadius: 8, fontSize: 12 }}
                formatter={(v) => formatCurrency(v)}
              />
              <Bar dataKey="total" fill="#E3A73C" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top merchants">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stats.merchant_frequency} layout="vertical" margin={{ left: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A3B36" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#7D8985", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis
                dataKey="merchant"
                type="category"
                width={90}
                tick={{ fill: "#B9C0BB", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip contentStyle={{ background: "#1B2925", border: "1px solid #2A3B36", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="count" fill="#3E8874" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <ListCard title="Category frequency">
          {stats.category_frequency.map((c) => (
            <div key={c.category} className="flex justify-between border-b border-line/60 py-2 text-sm last:border-0">
              <span className="capitalize text-ash-300">{c.category}</span>
              <span className="stat-figure text-ash-500">{c.count}</span>
            </div>
          ))}
        </ListCard>

        <ListCard title="Most expensive purchases">
          {stats.top_purchases.map((p, idx) => (
            <div key={idx} className="flex justify-between border-b border-line/60 py-2 text-sm last:border-0">
              <div className="min-w-0">
                <p className="truncate text-ash-300">{p.name}</p>
                <p className="text-xs text-ash-700">{p.merchant}</p>
              </div>
              <span className="stat-figure shrink-0 text-ash-100">{formatCurrency(p.price)}</span>
            </div>
          ))}
        </ListCard>
      </div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-ash-700">{label}</p>
      <p className="stat-figure mt-1 text-xl font-semibold text-ash-100">{value}</p>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <h2 className="mb-2 font-display text-sm font-medium text-ash-300">{title}</h2>
      {children}
    </div>
  );
}

function ListCard({ title, children }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <h2 className="mb-1 font-display text-sm font-medium text-ash-300">{title}</h2>
      {children}
    </div>
  );
}
