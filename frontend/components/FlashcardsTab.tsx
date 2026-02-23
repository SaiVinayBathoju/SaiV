"use client";

import { useState, useEffect } from "react";
import { Loader2, BookOpen } from "lucide-react";
import type { FlashcardItem } from "@/lib/api";

interface FlashcardsTabProps {
  documentId: string | null;
  onError: (msg: string) => void;
}

export default function FlashcardsTab({ documentId, onError }: FlashcardsTabProps) {
  const [flashcards, setFlashcards] = useState<FlashcardItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    if (!documentId) {
      setFlashcards([]);
      setCurrentIndex(0);
      return;
    }
    setLoading(true);
    setFlashcards([]);
    import("@/lib/api").then(({ generateFlashcards }) => {
      generateFlashcards(documentId).then((res) => {
        setLoading(false);
        if (res.success && res.data) {
          setFlashcards(res.data.flashcards);
          setCurrentIndex(0);
          setFlipped(false);
        } else {
          onError(res.error || "Failed to generate flashcards");
        }
      });
    });
  }, [documentId, onError]);

  if (!documentId) {
    return (
      <div className="flex flex-col items-center justify-center px-4 py-12 text-center text-zinc-500 sm:py-16 md:py-20">
        <BookOpen className="mb-3 h-12 w-12 opacity-50 sm:mb-4 sm:h-16 sm:w-16" />
        <p className="text-sm sm:text-base">Process a YouTube video or PDF first to generate flashcards.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 sm:py-16 md:py-20">
        <Loader2 className="mb-3 h-10 w-10 animate-spin text-saiv-500 sm:mb-4 sm:h-12 sm:w-12" />
        <p className="text-sm text-zinc-400 sm:text-base">Generating flashcards...</p>
      </div>
    );
  }

  if (flashcards.length === 0) {
    return (
      <div className="glass-card rounded-2xl px-4 py-12 text-center text-sm text-zinc-500 sm:py-16 md:py-20 md:text-base">
        No flashcards generated. Try different content.
      </div>
    );
  }

  const current = flashcards[currentIndex];

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-center gap-2 sm:flex-initial sm:gap-3">
          <div className="h-2 min-w-[60px] flex-1 overflow-hidden rounded-full bg-[var(--border)] sm:w-28 md:w-32">
            <div
              className="h-full rounded-full bg-saiv-500 transition-all duration-300"
              style={{ width: `${((currentIndex + 1) / flashcards.length) * 100}%` }}
            />
          </div>
          <p className="shrink-0 text-xs text-zinc-400 sm:text-sm">
            {currentIndex + 1} / {flashcards.length}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            onClick={() => {
              setCurrentIndex((i) => Math.max(0, i - 1));
              setFlipped(false);
            }}
            disabled={currentIndex === 0}
            className="min-h-[44px] min-w-[80px] touch-manipulation rounded-xl border border-[var(--border)] px-3 py-2 text-sm transition hover:bg-white/5 disabled:opacity-40 sm:min-h-0 sm:min-w-0 sm:px-4"
          >
            Previous
          </button>
          <button
            onClick={() => {
              setCurrentIndex((i) => Math.min(flashcards.length - 1, i + 1));
              setFlipped(false);
            }}
            disabled={currentIndex === flashcards.length - 1}
            className="min-h-[44px] min-w-[80px] touch-manipulation rounded-xl border border-[var(--border)] px-3 py-2 text-sm transition hover:bg-white/5 disabled:opacity-40 sm:min-h-0 sm:min-w-0 sm:px-4"
          >
            Next
          </button>
        </div>
      </div>

      <div
        onClick={() => setFlipped((f) => !f)}
        className="glass-card group relative min-h-[180px] cursor-pointer rounded-2xl p-5 transition hover:border-saiv-500/40 sm:min-h-[200px] sm:p-6 md:min-h-[220px] md:p-8"
      >
        <div className="text-center">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-saiv-500 sm:mb-2">
            {flipped ? "Answer" : "Question"}
          </p>
          <p className="text-base leading-relaxed text-zinc-100 sm:text-lg">
            {flipped ? current.answer : current.question}
          </p>
        </div>
        <p className="absolute bottom-3 left-1/2 -translate-x-1/2 text-xs text-zinc-500 opacity-0 transition group-hover:opacity-100 sm:bottom-4">
          Click to flip
        </p>
      </div>
    </div>
  );
}
