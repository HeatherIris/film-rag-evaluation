import { useEffect, useState } from "react";
import { ApiError, deleteMemory, listMemory } from "../api/client";
import { useAppOutlet } from "../App";
import type { Memory } from "../types";

export function MemoryPage() {
  const { conversations } = useAppOutlet();
  const [selectedId, setSelectedId] = useState("");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedId && conversations.length > 0) {
      setSelectedId(conversations[0].conversation_id);
    }
  }, [conversations, selectedId]);

  useEffect(() => {
    if (!selectedId) {
      setMemories([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    listMemory(selectedId)
      .then((items) => {
        if (!cancelled) setMemories(items);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setMemories([]);
          setError(err instanceof ApiError ? err.message : "Could not load memory.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function handleDelete(memoryId: string) {
    setError(null);
    try {
      await deleteMemory(memoryId);
      setMemories((current) => current.filter((item) => item.memory_id !== memoryId));
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "Could not delete memory.");
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <h1>Memory</h1>
      </header>
      <p className="muted">
        Memories are stored only when a message contains a clear preference, topic, or viewing habit.
        Ordinary questions are not saved.
      </p>
      {conversations.length === 0 ? (
        <div className="empty-state">
          <p className="empty-title">No conversations yet</p>
          <p className="muted">Start a chat to create memory.</p>
        </div>
      ) : (
        <label className="field">
          Conversation
          <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
            {conversations.map((item) => (
              <option key={item.conversation_id} value={item.conversation_id}>
                {item.title}
              </option>
            ))}
          </select>
        </label>
      )}
      {error && <div className="banner error">{error}</div>}
      {loading && <p className="muted">Loading memory…</p>}
      {!loading && selectedId && memories.length === 0 && (
        <div className="empty-state">
          <p className="empty-title">No memories yet</p>
          <p className="muted">No memories for this conversation.</p>
        </div>
      )}
      <ul className="memory-list">
        {memories.map((memory) => (
          <li key={memory.memory_id} className="memory-item">
            <div>
              <span className="memory-type">{memory.type}</span>
              <p>{memory.content}</p>
            </div>
            <button type="button" className="link-button" onClick={() => handleDelete(memory.memory_id)}>
              Delete
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
