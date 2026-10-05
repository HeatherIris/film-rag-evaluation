import type { ChatMode } from "../types";

const OPTIONS: { value: ChatMode; label: string }[] = [
  { value: "llm", label: "LLM only" },
  { value: "rag", label: "RAG" },
  { value: "rag_tmdb", label: "RAG + TMDB" },
];

type ModeSelectorProps = {
  value: ChatMode;
  onChange: (mode: ChatMode) => void;
  disabled?: boolean;
};

export function ModeSelector({ value, onChange, disabled }: ModeSelectorProps) {
  return (
    <div className="mode-selector" role="radiogroup" aria-label="Answer mode">
      {OPTIONS.map((option) => (
        <label key={option.value} className={value === option.value ? "mode-option selected" : "mode-option"}>
          <input
            type="radio"
            name="chat-mode"
            value={option.value}
            checked={value === option.value}
            disabled={disabled}
            onChange={() => onChange(option.value)}
          />
          {option.label}
        </label>
      ))}
    </div>
  );
}
