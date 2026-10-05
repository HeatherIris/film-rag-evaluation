import { useState } from "react";
import type { Source, ToolCallRecord } from "../types";

type ExpandableProps = {
  sources: Source[];
  tools: ToolCallRecord[];
};

export function ExpandableEvidence({ sources, tools }: ExpandableProps) {
  const [showSources, setShowSources] = useState(false);
  const [showTools, setShowTools] = useState(false);

  return (
    <>
      {tools.length > 0 && (
        <div className="tools evidence">
          <button type="button" className="sources-toggle" onClick={() => setShowTools((v) => !v)}>
            Tools · {tools.length}
          </button>
          {showTools &&
            tools.map((tool, index) => (
              <pre key={`${tool.name}-${index}`}>
                {tool.name}({JSON.stringify(tool.arguments)})
              </pre>
            ))}
        </div>
      )}
      {sources.length > 0 && (
        <div className="sources evidence">
          <button type="button" className="sources-toggle" onClick={() => setShowSources((v) => !v)}>
            Sources · {sources.length}
          </button>
          {showSources &&
            sources.map((source, index) => (
              <div key={`${source.filename}-${index}`} className="source-item">
                <strong>{source.filename}</strong>
                <span className="score">score {source.score.toFixed(3)}</span>
                <p>{source.chunk}</p>
              </div>
            ))}
        </div>
      )}
    </>
  );
}
