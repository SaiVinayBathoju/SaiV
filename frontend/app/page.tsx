"use client";

import { useState } from "react";
import InputPanel from "@/components/InputPanel";
import FlashcardsTab from "@/components/FlashcardsTab";
import QuizTab from "@/components/QuizTab";
import ChatTab from "@/components/ChatTab";

type Tab = "flashcards" | "quiz" | "chat";

export default function Home() {
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [documentTitle, setDocumentTitle] = useState<string>("");
  const [activeTab, setActiveTab] = useState<Tab>("flashcards");
  const [error, setError] = useState<string>("");

  const handleProcessed = (id: string, title: string) => {
    setDocumentId(id);
    setDocumentTitle(title);
    setError("");
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "flashcards", label: "Flashcards" },
    { id: "quiz", label: "Quiz" },
    { id: "chat", label: "Chat" },
  ];

  return (
    <main className="relative mx-auto min-h-screen min-h-[100dvh] w-full max-w-4xl pt-[calc(1.5rem+env(safe-area-inset-top))] pr-[calc(0.75rem+env(safe-area-inset-right))] pb-[calc(1.5rem+env(safe-area-inset-bottom))] pl-[calc(0.75rem+env(safe-area-inset-left))] sm:pt-[calc(2.5rem+env(safe-area-inset-top))] sm:pr-[calc(1.5rem+env(safe-area-inset-right))] sm:pb-[calc(2.5rem+env(safe-area-inset-bottom))] sm:pl-[calc(1.5rem+env(safe-area-inset-left))] md:pt-[calc(3rem+env(safe-area-inset-top))] md:pr-[calc(2rem+env(safe-area-inset-right))] md:pb-[calc(3rem+env(safe-area-inset-bottom))] md:pl-[calc(2rem+env(safe-area-inset-left))]">
      {/* Header */}
      <header className="mb-8 text-center sm:mb-10 md:mb-14">
        <div className="mb-2 inline-block rounded-full border border-saiv-500/30 bg-saiv-500/10 px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-saiv-400 sm:px-4 sm:py-1.5 sm:text-xs">
          AI-Powered Learning
        </div>
        <h1 className="font-display text-3xl font-bold tracking-tight text-white sm:text-4xl md:text-5xl lg:text-6xl">
          SaiV
        </h1>
        <p className="mt-2 max-w-xl mx-auto px-2 text-base text-zinc-400 sm:mt-3 sm:text-lg md:text-xl">
          Turn videos &amp; PDFs into <span className="text-saiv-400/90">flashcards</span>,{" "}
          <span className="text-saiv-400/90">quizzes</span>, and a personal{" "}
          <span className="text-saiv-400/90">chat tutor</span>.
        </p>
      </header>

      {/* Input Panel */}
      <section className="mb-8 sm:mb-12">
        <InputPanel onProcessed={handleProcessed} onError={setError} />
      </section>

      {/* Error Banner */}
      {error && (
        <div
          role="alert"
          className="mb-4 animate-fade-in rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm text-red-300 shadow-lg sm:mb-6 sm:px-4 sm:py-3"
        >
          {error}
        </div>
      )}

      {/* Results Section */}
      {documentId && (
        <section className="animate-fade-in">
          <div className="mb-4 flex items-center justify-between gap-2 sm:mb-5">
            <h2 className="min-w-0 truncate font-display text-lg font-semibold text-white sm:text-xl">
              {documentTitle || "Your Content"}
            </h2>
          </div>

          {/* Tabs - full width on mobile, pill row on larger */}
          <div className="mb-4 flex w-full gap-0.5 rounded-xl border border-[var(--border)] bg-[var(--card)]/60 p-1 backdrop-blur sm:mb-6 sm:w-auto sm:inline-flex">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`min-h-[44px] flex-1 rounded-lg px-3 py-2.5 text-sm font-medium transition-all touch-manipulation sm:flex-none sm:px-5 ${
                  activeTab === tab.id
                    ? "bg-saiv-600 text-white shadow-md"
                    : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="min-h-[280px] sm:min-h-[320px]">
            {activeTab === "flashcards" && (
              <FlashcardsTab documentId={documentId} onError={setError} />
            )}
            {activeTab === "quiz" && (
              <QuizTab documentId={documentId} onError={setError} />
            )}
            {activeTab === "chat" && (
              <ChatTab documentId={documentId} onError={setError} />
            )}
          </div>
        </section>
      )}

      {!documentId && (
        <div className="glass-card animate-fade-in rounded-2xl py-12 text-center sm:py-16 md:py-20">
          <p className="px-2 text-sm text-zinc-500 sm:text-base">
            Paste a <span className="text-zinc-400">YouTube</span> link or upload a{" "}
            <span className="text-zinc-400">PDF</span> above to get started.
          </p>
        </div>
      )}
    </main>
  );
}
