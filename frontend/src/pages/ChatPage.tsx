import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError, createConversation, getConversation, sendChatMessage } from "../api/client";
import { ChatInput } from "../components/ChatInput";
import { ChatMessage } from "../components/ChatMessage";
import { ModeSelector } from "../components/ModeSelector";
import type { ChatMode, Message } from "../types";
import { useAppOutlet } from "../App";

export function ChatPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { refreshConversations } = useAppOutlet();
  const [mode, setMode] = useState<ChatMode>("rag");
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const skipNextLoad = useRef(false);

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      setError(null);
      return;
    }
    if (skipNextLoad.current) {
      skipNextLoad.current = false;
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getConversation(conversationId)
      .then((detail) => {
        if (cancelled) return;
        setMessages(detail.messages);
        void refreshConversations();
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setMessages([]);
        setError(err instanceof ApiError ? err.message : "Could not load conversation.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId, refreshConversations]);

  async function handleSend(text: string) {
    setError(null);
    setSending(true);
    const pendingId = `local_${Date.now()}`;
    try {
      let activeId = conversationId;
      if (!activeId) {
        const created = await createConversation(titleFromMessage(text));
        await refreshConversations();
        activeId = created.conversation_id;
        skipNextLoad.current = true;
        navigate(`/chat/${activeId}`, { replace: true });
      }

      const pendingUser: Message = {
        message_id: pendingId,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
        mode,
      };
      setMessages((current) => [...current, pendingUser]);

      const reply = await sendChatMessage({
        conversation_id: activeId,
        message: text,
        mode,
      });

      const assistant: Message = {
        message_id: reply.message_id,
        role: "assistant",
        content: reply.answer,
        created_at: new Date().toISOString(),
        mode: reply.mode,
        latency_ms: reply.latency_ms,
        sources: reply.sources,
        tools: reply.tools,
      };
      setMessages((current) => [...current, assistant]);
      await refreshConversations();
    } catch (err: unknown) {
      setMessages((current) => current.filter((message) => message.message_id !== pendingId));
      setError(err instanceof ApiError ? err.message : "The request failed.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="page chat-page">
      <header className="page-header">
        <h1>Chat</h1>
        <ModeSelector value={mode} onChange={setMode} disabled={sending} />
      </header>
      {error && <div className="banner error">{error}</div>}
      <div className="message-list">
        {loading && <p className="muted">Loading conversation…</p>}
        {!loading && messages.length === 0 && (
          <div className="empty-state">
            <p className="empty-title">Ask a film question</p>
            <p className="muted">Start a conversation, or choose a thread in the sidebar.</p>
          </div>
        )}
        {messages.map((message) => (
          <ChatMessage key={message.message_id} message={message} />
        ))}
      </div>
      <ChatInput disabled={sending} onSend={handleSend} />
    </section>
  );
}

function titleFromMessage(message: string): string {
  const trimmed = message.trim().replace(/\s+/g, " ");
  return trimmed.length > 48 ? `${trimmed.slice(0, 48)}…` : trimmed || "New chat";
}
