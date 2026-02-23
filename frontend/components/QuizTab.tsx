"use client";

import { useState, useEffect } from "react";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import type { QuizItem } from "@/lib/api";

interface QuizTabProps {
  documentId: string | null;
  onError: (msg: string) => void;
}

export default function QuizTab({ documentId, onError }: QuizTabProps) {
  const [quiz, setQuiz] = useState<QuizItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);

  useEffect(() => {
    if (!documentId) {
      setQuiz([]);
      setCurrentIndex(0);
      setSelected(null);
      setShowResult(false);
      return;
    }
    setLoading(true);
    setQuiz([]);
    import("@/lib/api").then(({ generateQuiz }) => {
      generateQuiz(documentId).then((res) => {
        setLoading(false);
        if (res.success && res.data) {
          setQuiz(res.data.quiz);
          setCurrentIndex(0);
          setSelected(null);
          setShowResult(false);
        } else {
          onError(res.error || "Failed to generate quiz");
        }
      });
    });
  }, [documentId, onError]);

  if (!documentId) {
    return (
      <div className="flex flex-col items-center justify-center px-4 py-12 text-center text-zinc-500 sm:py-16 md:py-20">
        <p className="text-sm sm:text-base">Process a YouTube video or PDF first to generate a quiz.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 sm:py-16 md:py-20">
        <Loader2 className="mb-3 h-10 w-10 animate-spin text-saiv-500 sm:mb-4 sm:h-12 sm:w-12" />
        <p className="text-sm text-zinc-400 sm:text-base">Generating quiz...</p>
      </div>
    );
  }

  if (quiz.length === 0) {
    return (
      <div className="glass-card flex flex-col items-center justify-center rounded-2xl px-4 py-12 text-center sm:py-16 md:py-20">
        <p className="text-sm text-zinc-500 md:text-base">No quiz generated. Try different content.</p>
      </div>
    );
  }

  const current = quiz[currentIndex];
  const options = ["A", "B", "C", "D"].slice(0, current.options.length);
  const correctIndex = options.indexOf(current.correct_answer);
  const correctOption = correctIndex >= 0 ? current.options[correctIndex] : null;

  const handleSelect = (opt: string, idx: number) => {
    if (showResult) return;
    setSelected(current.options[idx]);
    setShowResult(true);
  };

  const goNext = () => {
    setCurrentIndex((i) => Math.min(quiz.length - 1, i + 1));
    setSelected(null);
    setShowResult(false);
  };

  const goPrev = () => {
    setCurrentIndex((i) => Math.max(0, i - 1));
    setSelected(null);
    setShowResult(false);
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-center gap-2 sm:flex-initial sm:gap-3">
          <div className="h-2 min-w-[60px] flex-1 overflow-hidden rounded-full bg-[var(--border)] sm:w-28 md:w-32">
            <div
              className="h-full rounded-full bg-saiv-500 transition-all duration-300"
              style={{ width: `${((currentIndex + 1) / quiz.length) * 100}%` }}
            />
          </div>
          <p className="shrink-0 text-xs text-zinc-400 sm:text-sm">
            Question {currentIndex + 1} / {quiz.length}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            onClick={goPrev}
            disabled={currentIndex === 0}
            className="min-h-[44px] min-w-[80px] touch-manipulation rounded-xl border border-[var(--border)] px-3 py-2 text-sm transition hover:bg-white/5 disabled:opacity-40 sm:min-h-0 sm:min-w-0 sm:px-4"
          >
            Previous
          </button>
          <button
            onClick={goNext}
            disabled={currentIndex === quiz.length - 1}
            className="min-h-[44px] min-w-[80px] touch-manipulation rounded-xl border border-[var(--border)] px-3 py-2 text-sm transition hover:bg-white/5 disabled:opacity-40 sm:min-h-0 sm:min-w-0 sm:px-4"
          >
            Next
          </button>
        </div>
      </div>

      <div className="glass-card rounded-2xl p-4 sm:p-6">
        <p className="mb-4 text-base font-medium text-zinc-100 sm:mb-6 sm:text-lg">{current.question}</p>
        <div className="space-y-2 sm:space-y-3">
          {current.options.map((opt, idx) => {
            const letter = options[idx];
            const isSelected = selected === opt;
            const isCorrect = opt === correctOption;
            const showCorrect = showResult && isCorrect;
            const showWrong = showResult && isSelected && !isCorrect;

            return (
              <button
                key={idx}
                onClick={() => handleSelect(opt, idx)}
                disabled={showResult}
                className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition sm:gap-4 sm:px-4 sm:py-3 ${
                  showCorrect
                    ? "border-green-500/50 bg-green-500/10"
                    : showWrong
                    ? "border-red-500/50 bg-red-500/10"
                    : "border-[var(--border)] hover:border-saiv-600/50 hover:bg-white/[0.03]"
                }`}
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/5 text-sm font-medium text-zinc-300 sm:h-9 sm:w-9">
                  {letter}
                </span>
                <span className="min-w-0 flex-1 break-words text-sm text-zinc-200 sm:text-base">{opt}</span>
                {showResult && (
                  <>
                    {showCorrect && <CheckCircle className="h-5 w-5 shrink-0 text-green-500" />}
                    {showWrong && <XCircle className="h-5 w-5 shrink-0 text-red-500" />}
                  </>
                )}
              </button>
            );
          })}
        </div>
        {showResult && current.explanation && (
          <div className="mt-4 rounded-xl border border-saiv-500/20 bg-saiv-500/10 p-3 text-sm sm:mt-5 sm:p-4">
            <p className="font-medium text-saiv-400">Explanation</p>
            <p className="mt-1 text-zinc-300">{current.explanation}</p>
          </div>
        )}
      </div>
    </div>
  );
}
