const STORAGE_KEY = "film-intelligence-conversations";

import type { ConversationSummary } from "../types";

export function loadConversationList(): ConversationSummary[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ConversationSummary[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveConversationList(items: ConversationSummary[]): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}
