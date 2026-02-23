"use client";

import { useState } from "react";
import { Youtube, FileText, Loader2 } from "lucide-react";

interface InputPanelProps {
  onProcessed: (documentId: string, title: string) => void;
  onError: (message: string) => void;
}

export default function InputPanel({ onProcessed, onError }: InputPanelProps) {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleProcessVideo = async () => {
    const url = youtubeUrl.trim();
    if (!url) {
      onError("Please enter a YouTube URL");
      return;
    }
    if (
      !url.includes("youtube.com") &&
      !url.includes("youtu.be")
    ) {
      onError("Please enter a valid YouTube URL");
      return;
    }

    setLoading(true);
    onError("");
    try {
      const { processVideo } = await import("@/lib/api");
      const res = await processVideo(url);
      if (res.success && res.data) {
        onProcessed(res.data.document_id, res.data.title);
      } else {
        onError(res.error || "Failed to process video");
      }
    } catch (e) {
      onError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = async (file: File | null) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      onError("Please upload a PDF file");
      return;
    }

    setLoading(true);
    onError("");
    try {
      const { processPdf } = await import("@/lib/api");
      const res = await processPdf(file);
      if (res.success && res.data) {
        onProcessed(res.data.document_id, res.data.title);
      } else {
        onError(res.error || "Failed to process PDF");
      }
    } catch (e) {
      onError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileChange(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* YouTube Input */}
      <div className="glass-card rounded-2xl p-4 shadow-[var(--shadow-card)] sm:p-6">
        <label className="mb-2 flex items-center gap-2 font-display text-sm font-medium text-saiv-400 sm:mb-3">
          <Youtube className="h-4 w-4 shrink-0" />
          YouTube Video
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="url"
            placeholder="Paste YouTube URL..."
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleProcessVideo()}
            disabled={loading}
            className="min-h-[44px] flex-1 rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-3 text-base text-foreground placeholder:text-zinc-500 focus:border-saiv-500 focus:outline-none focus:ring-2 focus:ring-saiv-500/30 disabled:opacity-60 [font-size:16px] sm:min-h-0 sm:[font-size:inherit]"
          />
          <button
            onClick={handleProcessVideo}
            disabled={loading}
            className="flex min-h-[44px] touch-manipulation items-center justify-center gap-2 rounded-xl bg-saiv-600 px-5 py-3 font-medium text-white shadow-md transition hover:bg-saiv-500 hover:shadow-lg disabled:opacity-60 sm:min-h-0 sm:px-6"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Process"
            )}
          </button>
        </div>
      </div>

      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-[var(--border)]" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-[var(--background)] px-4 text-sm text-zinc-500">
            or
          </span>
        </div>
      </div>

      {/* PDF Upload */}
      <div className="glass-card rounded-2xl p-4 shadow-[var(--shadow-card)] sm:p-6">
        <label className="mb-2 flex items-center gap-2 font-display text-sm font-medium text-accent-400 sm:mb-3">
          <FileText className="h-4 w-4 shrink-0" />
          Upload PDF
        </label>
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 transition sm:px-6 sm:py-12 ${
            dragOver
              ? "border-saiv-500 bg-saiv-500/10"
              : "border-[var(--border)] hover:border-saiv-600/50 hover:bg-[var(--card-hover)]/50"
          }`}
        >
          <FileText className="mb-2 h-10 w-10 text-zinc-500 sm:mb-3 sm:h-12 sm:w-12" />
          <p className="mb-2 text-center text-xs text-zinc-400 sm:text-sm">
            Drag & drop your PDF here or choose a file
          </p>
          <input
            id="pdf-upload"
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileChange(file);
              e.target.value = "";
            }}
            disabled={loading}
          />
          <label
            htmlFor="pdf-upload"
            className="min-h-[44px] flex cursor-pointer touch-manipulation items-center justify-center rounded-xl bg-saiv-600 px-5 py-2.5 text-sm font-medium text-white shadow-md transition hover:bg-saiv-500 disabled:pointer-events-none disabled:opacity-60"
          >
            {loading ? "Uploading…" : "Choose PDF file"}
          </label>
          <p className="mt-2 text-center text-xs text-zinc-600">Max 10MB • PDF only</p>
        </div>
      </div>
    </div>
  );
}
