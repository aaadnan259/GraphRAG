import React, { useState } from "react";
import { ChatView } from "@/views/ChatView";
import { KnowledgeBaseView } from "@/views/KnowledgeBaseView";
import { GraphExplorerView } from "@/views/GraphExplorerView";
import { Sidebar } from "@/components/Sidebar";
import "./App.css";

export default function App() {
  const [activePage, setActivePage] = useState<'chat' | 'knowledge' | 'graph'>('chat');

  return (
    <div className="app-container">
      <Sidebar activePage={activePage} setActivePage={setActivePage} />

      <main className="main-content">
        {activePage === 'chat' && <ChatView />}
        {activePage === 'knowledge' && <KnowledgeBaseView />}
        {activePage === 'graph' && <GraphExplorerView />}
      </main>
    </div>
  );
}
