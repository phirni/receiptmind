import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Trash2, AlertTriangle } from "lucide-react";
import { api, ApiError } from "../api/client.js";
import { Spinner } from "../components/Status.jsx";
import { formatCurrency, formatDateTime } from "../lib/format.js";
import { useToast } from "../components/Toast.jsx";

export default function ReceiptDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [receipt, setReceipt] = useState(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .getReceipt(id)
      .then((r) => !cancelled && setReceipt(r))
      .catch((err) => !cancelled && toast.error(err instanceof ApiError ? err.message : "Receipt not found."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [id, toast]);

  const handleDelete = async () => {
    if (!confirm("Delete this receipt? This can't be undone.")) return;
    try {
      await api.deleteReceipt(id);
      toast.success("Receipt deleted.");
      navigate("/receipts");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete receipt.");
    }
  };

  if (loading) return <Spinner label="Loading receipt…" />;
  if (!receipt) return null;

  const lowConfidence = receipt.confidence !== null && receipt.confidence < 0.6;

  return (
    <div className="mx-auto max-w-4xl">
      <Link to="/receipts" className="focus-ring mb-6 inline-flex items-center gap-1.5 rounded text-sm text-ash-500 hover:text-amber">
        <ArrowLeft size={14} /> Back to receipts
      </Link>

      <div className="grid gap-8 md:grid-cols-2">
        <div className="rounded-lg border border-line bg-surface p-2">
          <img
            src={api.imageUrl(receipt.image_path)}
            alt={`Receipt from ${receipt.merchant_name}`}
            className="w-full rounded object-contain"
          />
        </div>

        <div>
          <div className="mb-4 flex items-start justify-between">
            <div>
              <h1 className="font-display text-xl font-semibold text-ash-100">{receipt.merchant_name}</h1>
              {receipt.merchant_address && <p className="text-xs text-ash-500">{receipt.merchant_address}</p>}
              <p className="mt-1 text-xs text-ash-500">{formatDateTime(receipt.purchase_datetime)}</p>
            </div>
            <button onClick={handleDelete} className="focus-ring rounded p-1.5 text-ash-700 hover:text-danger">
              <Trash2 size={16} />
            </button>
          </div>

          {lowConfidence && (
            <div className="mb-4 flex items-start gap-2 rounded-md border border-amber/30 bg-amber/10 px-3 py-2 text-xs text-amber">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <span>
                Low-confidence extraction ({Math.round(receipt.confidence * 100)}%). Double-check the amounts against the
                image.
              </span>
            </div>
          )}

          <div className="receipt-edge rounded-t-lg border border-line bg-raised p-5 font-mono text-sm">
            <ul className="space-y-1.5">
              {receipt.line_items.map((item) => (
                <li key={item.id} className="flex justify-between gap-4 text-ash-300">
                  <span className="truncate">
                    {item.quantity !== 1 && <span className="text-ash-700">{item.quantity}× </span>}
                    {item.name}
                  </span>
                  <span className="shrink-0 text-ash-100">{formatCurrency(item.total_price, receipt.currency)}</span>
                </li>
              ))}
            </ul>

            <div className="mt-4 space-y-1 border-t border-dashed border-line pt-3 text-ash-300">
              {receipt.subtotal !== null && (
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span>{formatCurrency(receipt.subtotal, receipt.currency)}</span>
                </div>
              )}
              {receipt.tax !== null && (
                <div className="flex justify-between">
                  <span>Tax</span>
                  <span>{formatCurrency(receipt.tax, receipt.currency)}</span>
                </div>
              )}
              <div className="flex justify-between pt-1 text-base font-semibold text-amber">
                <span>Total</span>
                <span>{formatCurrency(receipt.total, receipt.currency)}</span>
              </div>
            </div>
          </div>

          <dl className="mt-6 grid grid-cols-2 gap-3 text-xs">
            {receipt.receipt_number && (
              <div>
                <dt className="text-ash-700">Receipt #</dt>
                <dd className="text-ash-300">{receipt.receipt_number}</dd>
              </div>
            )}
            {receipt.payment_method && (
              <div>
                <dt className="text-ash-700">Payment</dt>
                <dd className="text-ash-300">{receipt.payment_method}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
}
