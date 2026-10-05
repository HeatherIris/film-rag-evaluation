import { NavLink, useLocation } from "react-router-dom";
import type { ConversationSummary } from "../types";

type SidebarProps = {
  conversations: ConversationSummary[];
  activeId?: string;
  onNewChat: () => void;
  creating: boolean;
};

export function Sidebar({ conversations, activeId, onNewChat, creating }: SidebarProps) {
  const location = useLocation();
  const chatActive = location.pathname === "/" || location.pathname.startsWith("/chat/");

  return (
    <aside className="sidebar">
      <div className="brand">Film Intelligence</div>
      <button className="new-chat" type="button" onClick={onNewChat} disabled={creating}>
        {creating ? "Creating…" : "New Chat"}
      </button>
      <nav className="nav">
        <NavLink to="/" className={() => (chatActive ? "nav-link active" : "nav-link")}>
          Chat
        </NavLink>
        <NavLink
          to="/evaluation"
          className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
        >
          Evaluation
        </NavLink>
        <NavLink to="/memory" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
          Memory
        </NavLink>
      </nav>
      <div className="sidebar-label">Conversations</div>
      <ul className="conversation-list">
        {conversations.length === 0 ? (
          <li className="empty-list">No conversations yet</li>
        ) : (
          conversations.map((item) => (
            <li key={item.conversation_id}>
              <NavLink
                to={`/chat/${item.conversation_id}`}
                className={() =>
                  item.conversation_id === activeId ? "conversation-link active" : "conversation-link"
                }
              >
                {item.title}
              </NavLink>
            </li>
          ))
        )}
      </ul>
    </aside>
  );
}
