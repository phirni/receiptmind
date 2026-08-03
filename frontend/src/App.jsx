import React from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import { ToastProvider } from "./components/Toast.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import ReceiptsPage from "./pages/ReceiptsPage.jsx";
import ReceiptDetailPage from "./pages/ReceiptDetailPage.jsx";
import SearchPage from "./pages/SearchPage.jsx";
import StatisticsPage from "./pages/StatisticsPage.jsx";

export default function App() {
  return (
    <ToastProvider>
      <Navbar />
      <main className="mx-auto max-w-6xl px-6 py-10">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/receipts" element={<ReceiptsPage />} />
          <Route path="/receipts/:id" element={<ReceiptDetailPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/statistics" element={<StatisticsPage />} />
        </Routes>
      </main>
    </ToastProvider>
  );
}
