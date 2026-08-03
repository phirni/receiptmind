import React, { useCallback, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { UploadCloud, FileImage, CheckCircle2, XCircle, ArrowRight } from "lucide-react";
import clsx from "clsx";
import { api, ApiError } from "../api/client.js";
import { Spinner } from "../components/Status.jsx";
import { useToast } from "../components/Toast.jsx";

const ACCEPTED = ["image/jpeg", "image/jpg", "image/png", "image/webp", "application/pdf"];

export default function UploadPage() {
  const [files, setFiles] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const inputRef = useRef(null);
  const toast = useToast();

  const addFiles = useCallback((fileList) => {
    const incoming = Array.from(fileList).filter((f) => ACCEPTED.includes(f.type) || /\.(pdf|jpe?g|png|webp)$/i.test(f.name));
    if (incoming.length < fileList.length) {
      toast.error("Some files were skipped — only jpg, png, webp, and pdf are supported.");
    }
    setFiles((prev) => [...prev, ...incoming]);
  }, [toast]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const removeFile = (idx) => setFiles((prev) => prev.filter((_, i) => i !== idx));

  const runUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setProgress(0);
    setResults(null);
    try {
      const res = await api.uploadReceipts(files, setProgress);
      setResults(res);
      setFiles([]);
      if (res.accepted > 0) toast.success(`${res.accepted} receipt${res.accepted === 1 ? "" : "s"} processed.`);
      if (res.rejected > 0) toast.error(`${res.rejected} file${res.rejected === 1 ? "" : "s"} could not be processed.`);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Upload failed unexpectedly.";
      toast.error(message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-semibold text-ash-100">Upload receipts</h1>
        <p className="mt-1 text-sm text-ash-500">
          Drop in photos or PDFs of receipts. Each one is read by a multimodal model and indexed for search in the background.
        </p>
      </header>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={clsx(
          "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-16 text-center transition-colors",
          dragging ? "border-amber bg-teal-dim/30" : "border-line hover:border-teal-soft"
        )}
      >
        <UploadCloud size={28} className={dragging ? "text-amber" : "text-ash-500"} />
        <div>
          <p className="font-display text-sm font-medium text-ash-100">Drag & drop receipts here</p>
          <p className="mt-1 text-xs text-ash-500">or click to browse — jpg, png, webp, pdf</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED.join(",")}
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <div className="mt-5 space-y-2">
          {files.map((f, idx) => (
            <div key={`${f.name}-${idx}`} className="flex items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2">
              <FileImage size={16} className="shrink-0 text-teal-soft" />
              <span className="flex-1 truncate text-sm text-ash-300">{f.name}</span>
              <span className="text-xs text-ash-700">{(f.size / 1024).toFixed(0)} KB</span>
              <button onClick={() => removeFile(idx)} className="focus-ring text-ash-700 hover:text-danger">
                <XCircle size={15} />
              </button>
            </div>
          ))}

          <button
            onClick={runUpload}
            disabled={uploading}
            className="focus-ring mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-amber px-4 py-2.5 font-display text-sm font-semibold text-ink transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {uploading ? `Uploading… ${progress}%` : `Process ${files.length} receipt${files.length === 1 ? "" : "s"}`}
          </button>
        </div>
      )}

      {uploading && <Spinner label="Reading receipts and extracting line items…" />}

      {results && (
        <div className="mt-8 space-y-2">
          <h2 className="font-display text-sm font-semibold text-ash-100">Results</h2>
          {results.results.map((r, idx) => (
            <div key={idx} className="flex items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2.5">
              {r.status === "queued" ? (
                <CheckCircle2 size={16} className="shrink-0 text-success" />
              ) : (
                <XCircle size={16} className="shrink-0 text-danger" />
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-ash-100">{r.filename}</p>
                {r.detail && <p className="truncate text-xs text-ash-500">{r.detail}</p>}
              </div>
              {r.receipt_id && (
                <Link
                  to={`/receipts/${r.receipt_id}`}
                  className="focus-ring flex items-center gap-1 rounded px-2 py-1 text-xs text-teal-soft hover:text-amber"
                >
                  View <ArrowRight size={12} />
                </Link>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
