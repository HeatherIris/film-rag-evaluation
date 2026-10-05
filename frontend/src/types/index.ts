export type ChatMode = "llm" | "rag" | "rag_tmdb";

export type ConversationSummary = {
  conversation_id: string;
  title: string;
  updated_at: string;
};

export type ConversationCreated = {
  conversation_id: string;
  title: string;
  created_at: string;
};

export type ConversationList = {
  items: ConversationSummary[];
};

export type MemoryType = "preference" | "topic" | "fact" | "summary";

export type Memory = {
  memory_id: string;
  conversation_id: string;
  type: MemoryType;
  content: string;
  created_at: string;
};

export type MemoryList = {
  items: Memory[];
};

export type Message = {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  mode?: ChatMode | null;
  latency_ms?: number;
  sources?: Source[];
  tools?: ToolCallRecord[];
};

export type ConversationDetail = {
  conversation_id: string;
  title: string;
  messages: Message[];
};

export type Source = {
  filename: string;
  chunk: string;
  score: number;
};

export type ToolCallRecord = {
  name: string;
  arguments: Record<string, unknown>;
};

export type ChatResponse = {
  message_id: string;
  answer: string;
  mode: ChatMode;
  latency_ms: number;
  sources: Source[];
  tools: ToolCallRecord[];
};

export type EvaluationModeResult = {
  mode: ChatMode;
  answer?: string | null;
  latency_ms?: number | null;
  sources?: Source[];
  tools?: ToolCallRecord[];
  error?: string | null;
};

export type EvaluationCompareResponse = {
  question: string;
  results: EvaluationModeResult[];
};
