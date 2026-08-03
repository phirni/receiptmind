import React, { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, XCircle, Info, X } from "lucide-react";

const ToastContext = createContext(null);

let idCounter = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback(
    (message, variant = "info") => {
      const id = ++idCounter;
      setToasts((t) => [...t, { id, message, variant }]);
      setTimeout(() => dismiss(id), 5000);
    },
    [dismiss]
  );

  const toast = {
    success: (msg) => push(msg, "success"),
    error: (msg) => push(msg, "error"),
    info: (msg) => push(msg, "info"),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 w-80">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }) {
  const icons = {
    success: <CheckCircle2 size={18} className="text-success shrink-0" />,
    error: <XCircle size={18} className="text-danger shrink-0" />,
    info: <Info size={18} className="text-teal-soft shrink-0" />,
  };
  return (
    <div className="flex items-start gap-2 rounded-lg border border-line bg-raised px-4 py-3 shadow-lg">
      {icons[toast.variant]}
      <p className="text-sm text-ash-100 flex-1">{toast.message}</p>
      <button onClick={onDismiss} className="text-ash-500 hover:text-ash-100 focus-ring rounded">
        <X size={14} />
      </button>
    </div>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
