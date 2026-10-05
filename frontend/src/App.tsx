import { useCallback, useEffect, useMemo, useState } from "react";
import { Outlet, useLocation, useNavigate, useOutletContext } from "react-router-dom";
import { ApiError, createConversation, listConversations } from "./api/client";
import { Sidebar } from "./components/Sidebar";
import type { ConversationSummary } from "./types";

type AppContext = {
  conversations: ConversationSummary[];
  refreshConversations: () => Promise<void>;
};

export function useAppOutlet(): AppContext {
  return useOutletContext<AppContext>();
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const conversationId = location.pathname.startsWith("/chat/")
    ? location.pathname.slice("/chat/".length)
    : undefined;
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshConversations = useCallback(async () => {
    const items = await listConversations();
    setConversations(items);
  }, []);

  useEffect(() => {
    refreshConversations().catch((err: unknown) => {
      setError(err instanceof ApiError ? err.message : "Could not load conversations.");
    });
  }, [refreshConversations]);

  async function handleNewChat() {
    setError(null);
    setCreating(true);
    try {
      const created = await createConversation("New chat");
      await refreshConversations();
      navigate(`/chat/${created.conversation_id}`);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "Could not create a conversation.");
    } finally {
      setCreating(false);
    }
  }

  const context = useMemo(
    () => ({ conversations, refreshConversations }),
    [conversations, refreshConversations],
  );

  return (
    <div className="app-shell">
      <Sidebar
        conversations={conversations}
        activeId={conversationId}
        onNewChat={handleNewChat}
        creating={creating}
      />
      <main className="main">
        {error && <div className="banner error">{error}</div>}
        <Outlet context={context} />
      </main>
    </div>
  );
}
