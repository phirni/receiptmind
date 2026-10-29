const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message, status, errorCode) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: options.body instanceof FormData ? options.headers : { "Content-Type": "application/json", ...options.headers },
  });

  if (!res.ok) {
    let detail = res.statusText;
    let errorCode = null;
    try {
      const body = await res.json();
      detail = body.detail || detail;
      errorCode = body.error_code || null;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status, errorCode);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => request("/health"),

  uploadReceipts: (files, onProgress) =>
    new Promise((resolve, reject) => {
      const formData = new FormData();
      for (const f of files) formData.append("files", f);

      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${BASE_URL}/upload`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          let detail = xhr.statusText;
          try {
            detail = JSON.parse(xhr.responseText).detail || detail;
          } catch {
            /* ignore */
          }
          reject(new ApiError(detail, xhr.status));
        }
      };
      xhr.onerror = () => reject(new ApiError("Network error during upload", 0));
      xhr.send(formData);
    }),

  listReceipts: (params = {}) => {
    const query = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ""))
    );
    return request(`/receipts?${query.toString()}`);
  },

  getReceipt: (id) => request(`/receipts/${id}`),
  deleteReceipt: (id) => request(`/receipts/${id}`, { method: "DELETE" }),

  search: (payload) => request("/search", { method: "POST", body: JSON.stringify(payload) }),
  reindex: () => request("/reindex", { method: "POST" }),
  getStats: () => request("/stats"),

  imageUrl: (path) => {
    // Local SQLite stores an absolute path; Supabase stores just the object key.
    const filename = path?.replaceAll("\\", "/").split("/").pop();
    return filename ? `${BASE_URL}/images/${encodeURIComponent(filename)}` : null;
  },
};
