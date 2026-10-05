import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App.tsx";
import { ChatPage } from "./pages/ChatPage.tsx";
import { EvaluationPage } from "./pages/EvaluationPage.tsx";
import { MemoryPage } from "./pages/MemoryPage.tsx";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<ChatPage />} />
          <Route path="chat/:conversationId" element={<ChatPage />} />
          <Route path="evaluation" element={<EvaluationPage />} />
          <Route path="memory" element={<MemoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
