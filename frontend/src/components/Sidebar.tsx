import React from "react";
import { IconChat, IconDatabase, IconGraph } from "@/components/Icons";
import { StatusIndicator } from "./StatusIndicator";

interface SidebarProps {
  activePage: 'chat' | 'knowledge' | 'graph';
  setActivePage: (page: 'chat' | 'knowledge' | 'graph') => void;
}

export const Sidebar = ({ activePage, setActivePage }: SidebarProps) => {
  return (
    <aside className="sidebar">
      <div className="logo-container">
         <h1 className="gradient-text logo-text">GraphRAG</h1>
      </div>

      <nav className="nav-menu">
        <button
          className={`nav-button ${activePage === 'chat' ? 'active' : ''}`}
          onClick={() => setActivePage('chat')}
        >
          <IconChat /> Chat
        </button>
        <button
          className={`nav-button ${activePage === 'knowledge' ? 'active' : ''}`}
          onClick={() => setActivePage('knowledge')}
        >
          <IconDatabase /> Knowledge Base
        </button>
        <button
          className={`nav-button ${activePage === 'graph' ? 'active' : ''}`}
          onClick={() => setActivePage('graph')}
        >
          <IconGraph /> Explorer
        </button>
      </nav>

      <StatusIndicator />
    </aside>
  );
};
