import { useState } from "react";
import type { FormEvent } from "react";

type ChatInputProps = {
  disabled?: boolean;
  onSend: (message: string) => void;
};

export function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const message = value.trim();
    if (!message || disabled) return;
    onSend(message);
    setValue("");
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <textarea
        rows={2}
        value={value}
        disabled={disabled}
        placeholder="Ask about a film…"
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            handleSubmit(event);
          }
        }}
      />
      <button className="send-button" type="submit" disabled={disabled || !value.trim()}>
        Send
      </button>
    </form>
  );
}
