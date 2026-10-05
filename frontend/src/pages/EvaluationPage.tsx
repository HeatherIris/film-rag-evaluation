import { useState } from "react";
import { ApiError, compareEvaluation } from "../api/client";
import { ExpandableEvidence } from "../components/ExpandableEvidence";
import type { ChatMode, EvaluationCompareResponse } from "../types";

const MODES: { value: ChatMode; label: string }[] = [
  { value: "llm", label: "LLM only" },
  { value: "rag", label: "RAG" },
  { value: "rag_tmdb", label: "RAG + TMDB" },
];

const MODE_LABEL: Record<ChatMode, string> = {
  llm: "LLM only",
  rag: "RAG",
  rag_tmdb: "RAG + TMDB",
};

export function EvaluationPage() {
  const [question, setQuestion] = useState("");
  const [selected, setSelected] = useState<ChatMode[]>(["llm", "rag", "rag_tmdb"]);
  const [comparison, setComparison] = useState<EvaluationCompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  function toggle(mode: ChatMode) {
    setSelected((current) =>
      current.includes(mode) ? current.filter((item) => item !== mode) : [...current, mode],
    );
  }

  async function handleCompare() {
    const trimmed = question.trim();
    if (!trimmed || selected.length === 0) return;
    setError(null);
    setRunning(true);
    try {
      const result = await compareEvaluation({ question: trimmed, modes: selected });
      setComparison(result);
    } catch (err: unknown) {
      setComparison(null);
      setError(err instanceof ApiError ? err.message : "Comparison failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="page evaluation-page">
      <header className="page-header">
        <h1>Evaluation</h1>
      </header>
      <p className="muted">Run the same film question through each selected mode. Results are not saved to chat history.</p>
      <label className="field">
        Question
        <textarea
          rows={4}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Enter a film question to compare across modes"
        />
      </label>
      <div className="checkbox-row">
        {MODES.map((mode) => (
          <label
            key={mode.value}
            className={selected.includes(mode.value) ? "mode-chip selected" : "mode-chip"}
          >
            <input
              type="checkbox"
              checked={selected.includes(mode.value)}
              onChange={() => toggle(mode.value)}
            />
            {mode.label}
          </label>
        ))}
      </div>
      <button
        type="button"
        className="primary-button"
        disabled={running || !question.trim() || selected.length === 0}
        onClick={() => void handleCompare()}
      >
        {running ? "Comparing…" : "Compare"}
      </button>
      {error && <div className="banner error">{error}</div>}
      {comparison && (
        <div className="compare-grid">
          {comparison.results.map((result) => (
            <article key={result.mode} className="result-panel">
              <h2>{MODE_LABEL[result.mode]}</h2>
              {result.error ? (
                <div className="banner error">{result.error}</div>
              ) : (
                <>
                  <div className="result-meta">
                    <span className="meta-badge">
                      {((result.latency_ms ?? 0) / 1000).toFixed(2)}s
                    </span>
                    <span className="meta-badge">{result.sources?.length ?? 0} sources</span>
                    <span className="meta-badge">{result.tools?.length ?? 0} tools</span>
                  </div>
                  <div className="message-body">{result.answer}</div>
                  <ExpandableEvidence
                    sources={result.sources ?? []}
                    tools={result.tools ?? []}
                  />
                </>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
