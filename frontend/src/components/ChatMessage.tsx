import { ExpandableEvidence } from "./ExpandableEvidence";
import type { Message } from "../types";

type ChatMessageProps = {
  message: Message;
};

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const sources = message.sources ?? [];
  const tools = message.tools ?? [];

  return (
    <article className={isUser ? "message user" : "message assistant"}>
      <div className="message-meta">
        <span>{isUser ? "You" : "Assistant"}</span>
        {!isUser && (
          <span className="meta-badges">
            {message.latency_ms != null && (
              <span className="meta-badge">Latency · {(message.latency_ms / 1000).toFixed(2)}s</span>
            )}
            {sources.length > 0 && <span className="meta-badge">Sources · {sources.length}</span>}
            {tools.length > 0 && <span className="meta-badge">Tools · {tools.length}</span>}
          </span>
        )}
      </div>
      <div className="message-body">{message.content}</div>
      {!isUser && <ExpandableEvidence sources={sources} tools={tools} />}
    </article>
  );
}
