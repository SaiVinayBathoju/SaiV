/**
 * API client for SaiV backend.
 * Uses /api/backend proxy in dev (see next.config.js rewrites).
 */

const API_BASE =
  typeof window !== "undefined"
    ? "/api/backend"
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ProcessContentResponse {
  document_id: string;
  title: string;
  content_preview: string;
  chunk_count: number;
  message: string;
}

export interface FlashcardItem {
  question: string;
  answer: string;
}

export interface FlashcardsResponse {
  flashcards: FlashcardItem[];
  document_id: string;
  count: number;
}

export interface QuizItem {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

export interface QuizResponse {
  quiz: QuizItem[];
  document_id: string;
  count: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    return {
      success: false,
      error: json.detail || json.error || "Request failed",
    };
  }
  return { success: true, data: json.data ?? json };
}

export async function processVideo(url: string) {
  return fetchApi<ProcessContentResponse>("/process-video", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function processPdf(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const url = `${API_BASE}/process-pdf`;
  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = json.detail;
    const errMsg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail) && detail[0]?.msg
          ? detail[0].msg
          : json.error || "Upload failed";
    return {
      success: false as const,
      error: errMsg,
    };
  }
  return {
    success: true as const,
    data: json.data ?? json,
  };
}

export async function generateFlashcards(documentId: string) {
  return fetchApi<FlashcardsResponse>("/generate-flashcards", {
    method: "POST",
    body: JSON.stringify({ document_id: documentId }),
  });
}

export async function generateQuiz(documentId: string) {
  return fetchApi<QuizResponse>("/generate-quiz", {
    method: "POST",
    body: JSON.stringify({ document_id: documentId }),
  });
}

export async function chatStream(
  documentId: string,
  messages: { role: string; content: string }[],
  onChunk: (text: string) => void,
  onError?: (err: string) => void
): Promise<void> {
  const url = `${API_BASE}/chat`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, messages }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    onError?.(err.detail || "Chat failed");
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError?.("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data.startsWith("[ERROR]")) {
          onError?.(data.slice(7));
          return;
        }
        onChunk(data);
      }
    }
  }
}
