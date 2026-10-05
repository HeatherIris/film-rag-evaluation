import type {
  ChatMode,
  ChatResponse,
  ConversationCreated,
  ConversationDetail,
  ConversationList,
  ConversationSummary,
  EvaluationCompareResponse,
  MemoryList,
} from "../types";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function quotaMessage(status: number, detail: string): string | null {
  const text = detail.toLowerCase();
  if (
    status === 429 ||
    text.includes("quota") ||
    text.includes("insufficient_quota") ||
    text.includes("credit") ||
    text.includes("rate limit")
  ) {
    return "AI service is temporarily unavailable due to API quota.";
  }
  return null;
}

function detailFromBody(body: unknown): string {
  if (typeof body === "string" && body.trim()) return body;
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    return JSON.stringify(detail);
  }
  return "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError("Cannot reach the API. Start the backend on port 8000.", 0);
  }

  let body: unknown = null;
  const raw = await response.text();
  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      body = raw;
    }
  }

  if (!response.ok) {
    const detail = detailFromBody(body) || response.statusText;
    const quota = quotaMessage(response.status, `${detail} ${raw}`);
    throw new ApiError(quota ?? detail, response.status);
  }

  return body as T;
}

export function listConversations(): Promise<ConversationSummary[]> {
  return request<ConversationList>("/api/conversations").then((body) => body.items);
}

export function createConversation(title: string): Promise<ConversationCreated> {
  return request<ConversationCreated>("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export function getConversation(conversationId: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/api/conversations/${conversationId}`);
}

export function sendChatMessage(payload: {
  conversation_id: string;
  message: string;
  mode: ChatMode;
}): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listMemory(conversationId: string): Promise<MemoryList["items"]> {
  return request<MemoryList>(`/api/memory/${conversationId}`).then((body) => body.items);
}

export function deleteMemory(memoryId: string): Promise<void> {
  return request<void>(`/api/memory/${memoryId}`, { method: "DELETE" });
}

export function compareEvaluation(payload: {
  question: string;
  modes: ChatMode[];
}): Promise<EvaluationCompareResponse> {
  return request<EvaluationCompareResponse>("/api/evaluation/compare", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
