"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatTabProps {
  documentId: string | null;
  onError: (msg: string) => void;
}

export default function ChatTab({ documentId, onError }: ChatTabProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || !documentId || streaming) return;

    const userMsg: Message = { role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setStreaming(true);

    // Placeholder for assistant message
    setMessages((m) => [...m, { role: "assistant", content: "" }]);

    const { chatStream } = await import("@/lib/api");
    let fullContent = "";

    await chatStream(
      documentId,
      [...messages, userMsg].map((m) => ({ role: m.role, content: m.content })),
      (chunk) => {
        fullContent += chunk;
        setMessages((m) => {
          const next = [...m];
          next[next.length - 1] = { role: "assistant", content: fullContent };
          return next;
        });
      },
      (err) => {
        onError(err);
        setMessages((m) => m.slice(0, -1));
      }
    );

    setStreaming(false);
  };

  if (!documentId) {
    return (
      <div className="flex flex-col items-center justify-center px-4 py-12 text-center text-zinc-500 sm:py-16 md:py-20">
        <p className="text-sm sm:text-base">Process a YouTube video or PDF first to chat with SaiV.</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-[320px] flex-col sm:min-h-[380px] md:h-[420px] md:min-h-[420px]">
      <div className="mb-3 rounded-xl border border-saiv-500/20 bg-saiv-500/5 px-3 py-2.5 text-xs text-saiv-200 sm:mb-4 sm:px-4 sm:py-3 sm:text-sm">
        Ask questions about your material. Answers are grounded in the content you processed.
      </div>

      <div className="glass-card flex min-h-0 flex-1 flex-col space-y-3 overflow-y-auto rounded-2xl p-3 sm:space-y-4 sm:p-4">
        {messages.length === 0 ? (
          <div className="flex min-h-[160px] flex-1 flex-col items-center justify-center gap-2 px-2 text-center text-zinc-500 sm:min-h-[200px]">
            <p className="text-sm sm:text-base">Ask anything about your material.</p>
            <p className="text-xs text-zinc-600">e.g. &quot;Summarize the main points&quot;</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`flex shrink-0 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[92%] rounded-2xl px-3 py-2.5 sm:max-w-[85%] sm:px-4 sm:py-3 ${
                  msg.role === "user"
                    ? "bg-saiv-600 text-white"
                    : "border border-[var(--border)] bg-white/5 text-zinc-200"
                }`}
              >
                <p className="whitespace-pre-wrap break-words text-sm">{msg.content || ""}</p>
                {streaming && i === messages.length - 1 && msg.role === "assistant" && (
                  <span className="inline-block h-4 w-2 animate-pulse bg-saiv-400" />
                )}
              </div>
            </div>
          ))
        )}
        <div ref={scrollRef} />
      </div>

      <div className="mt-3 flex min-h-0 shrink-0 gap-2 sm:mt-4 sm:gap-3">
        <input
          type="text"
          placeholder="Ask about your material..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
          disabled={streaming}
          className="min-h-[44px] min-w-0 flex-1 rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2.5 text-base text-foreground placeholder:text-zinc-500 focus:border-saiv-500 focus:outline-none focus:ring-2 focus:ring-saiv-500/30 disabled:opacity-60 sm:px-4 sm:py-3 [font-size:16px]"
        />
        <button
          onClick={sendMessage}
          disabled={streaming || !input.trim()}
          className="flex min-h-[44px] min-w-[44px] touch-manipulation items-center justify-center gap-2 rounded-xl bg-saiv-600 px-4 py-3 font-medium text-white shadow-md transition hover:bg-saiv-500 disabled:opacity-60 sm:min-w-0 sm:px-5"
        >
          {streaming ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
