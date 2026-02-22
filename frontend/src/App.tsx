import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "@/services/api";
import { IconChat, IconDatabase, IconGraph } from "@/components/Icons";
import { ChatView } from "@/views/ChatView";
import { KnowledgeBaseView } from "@/views/KnowledgeBaseView";
import { GraphExplorerView } from "@/views/GraphExplorerView";

// --- Styled Components (using React Styles for simplicity) ---

const styles = {
  appContainer: {
    display: 'flex',
    height: '100vh',
    width: '100vw',
    backgroundColor: 'var(--bg-app)',
    color: 'var(--text-primary)',
  },
  sidebar: {
    width: '260px',
    backgroundColor: 'var(--bg-sidebar)',
    borderRight: '1px solid var(--border-glass)',
    display: 'flex',
    flexDirection: 'column' as const,
    padding: '24px',
    gap: '24px',
    zIndex: 20,
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
    position: 'relative' as const,
    backgroundColor: 'var(--bg-app)',
  },
  navButton: (active: boolean) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    backgroundColor: active ? 'rgba(124, 58, 237, 0.1)' : 'transparent',
    color: active ? '#fff' : 'var(--text-secondary)',
    fontWeight: active ? 600 : 500,
    transition: 'all 0.2s ease',
    border: active ? '1px solid rgba(124, 58, 237, 0.2)' : '1px solid transparent',
    width: '100%',
    textAlign: 'left' as const,
    fontSize: '14px',
  }),
  statusDot: (online: boolean) => ({
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: online ? 'var(--success)' : 'var(--error)',
    boxShadow: online ? '0 0 8px var(--success)' : 'none',
    marginRight: '8px',
  }),
};

export default function App() {
  const [activePage, setActivePage] = useState<'chat' | 'knowledge' | 'graph'>('chat');
  const [backendStatus, setBackendStatus] = useState<boolean>(false);

  useEffect(() => {
    // Check backend connectivity on mount
    const checkBackend = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/`);
        setBackendStatus(response.ok);
      } catch {
        setBackendStatus(false);
      }
    };
    checkBackend();
    // Check every 30 seconds
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={styles.appContainer}>
      <aside style={styles.sidebar}>
        {/* Gradient Logo */}
        <div style={{ marginBottom: '12px' }}>
           <h1 className="gradient-text" style={{ fontSize: '24px', fontWeight: 800, letterSpacing: '-0.5px', margin: 0 }}>GraphRAG</h1>
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <button style={styles.navButton(activePage === 'chat')} onClick={() => setActivePage('chat')}>
            <IconChat /> Chat
          </button>
          <button style={styles.navButton(activePage === 'knowledge')} onClick={() => setActivePage('knowledge')}>
            <IconDatabase /> Knowledge Base
          </button>
          <button style={styles.navButton(activePage === 'graph')} onClick={() => setActivePage('graph')}>
            <IconGraph /> Explorer
          </button>
        </nav>

        {/* System Status Pod */}
        <div className="glass-card" style={{ padding: '16px', borderRadius: '12px', background: 'rgba(255,255,255,0.02)' }}>
          <h4 style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', margin: '0 0 12px 0', letterSpacing: '0.5px' }}>Server Status</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={styles.statusDot(backendStatus)} /> FastAPI Backend
            </div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={styles.statusDot(backendStatus)} /> Neo4j Graph
            </div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
               <div style={styles.statusDot(backendStatus)} /> Chroma Vector
            </div>
          </div>
        </div>
      </aside>

      <main style={styles.main}>
        {activePage === 'chat' && <ChatView />}
        {activePage === 'knowledge' && <KnowledgeBaseView />}
        {activePage === 'graph' && <GraphExplorerView />}
      </main>
    </div>
  );
}
