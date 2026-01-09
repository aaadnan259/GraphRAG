import React, { useState, useEffect, useRef } from "react";
import ReactDOM from "react-dom/client";

// --- Configuration & Types ---

const API_BASE_URL = "http://localhost:8000";

interface Message {
  role: "user" | "model";
  content: string;
  sources?: string[];
  isGraphAugmented?: boolean;
}

interface IngestionRecord {
  document_id: string;
  filename: string;
  timestamp: string;
  num_entities: number;
  num_relationships: number;
}

interface GraphStats {
  total_entities: number;
  total_relationships: number;
  entity_types: Record<string, number>;
  relationship_types: Record<string, number>;
}

// --- API Service Layer ---

class APIService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async query(queryText: string, useVector: boolean = true, useGraph: boolean = true): Promise<any> {
    const response = await fetch(`${this.baseUrl}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: queryText,
        use_vector_search: useVector,
        use_graph_search: useGraph,
      }),
    });

    if (!response.ok) {
      throw new Error(`Query failed: ${response.statusText}`);
    }

    return await response.json();
  }

  async ingest(file: File): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${this.baseUrl}/ingest`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Ingestion failed: ${response.statusText}`);
    }

    return await response.json();
  }

  async getStats(): Promise<GraphStats> {
    const response = await fetch(`${this.baseUrl}/stats`);

    if (!response.ok) {
      throw new Error(`Stats fetch failed: ${response.statusText}`);
    }

    return await response.json();
  }

  async searchEntities(query: string, limit: number = 10): Promise<any> {
    const response = await fetch(`${this.baseUrl}/search/entities?query=${encodeURIComponent(query)}&limit=${limit}`);

    if (!response.ok) {
      throw new Error(`Entity search failed: ${response.statusText}`);
    }

    return await response.json();
  }
}

const api = new APIService();

// --- Icons (SVG Components) ---

const IconChat = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
);
const IconDatabase = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
);
const IconGraph = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
);
const IconCheck = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
);
const IconUpload = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
);
const IconSearch = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
);
const IconChevronDown = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
);

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

// --- View Components ---

// 1. Chat View (Hero View)
const ChatView = () => {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'model', content: "Welcome to Graph Intelligence. I am ready to analyze your data using vector similarity and knowledge graph traversal." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input;
    setInput("");
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
        // Call FastAPI backend
        const response = await api.query(userMsg, true, true);

        if (response && response.answer) {
            setMessages(prev => [...prev, { 
                role: 'model', 
                content: response.answer,
                isGraphAugmented: response.sources && response.sources.length > 0,
                sources: response.sources || []
            }]);
        }
    } catch (e) {
        console.error("Query error:", e);
        setMessages(prev => [...prev, { 
            role: 'model', 
            content: `I encountered an error: ${e instanceof Error ? e.message : 'Unknown error'}. Please ensure the backend is running on port 8000.` 
        }]);
    } finally {
        setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{ padding: '20px 32px', borderBottom: '1px solid var(--border-glass)', backdropFilter: 'blur(10px)', zIndex: 10 }}>
        <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>Graph Intelligence</h2>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Hybrid Retrieval • Gemini 2.5 Flash</div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '32px', display: 'flex', flexDirection: 'column', gap: '32px' }}>
        {messages.map((msg, idx) => (
          <div key={idx} className="animate-fade-in" style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '800px',
              margin: msg.role === 'user' ? '0 0 0 auto' : '0 auto 0 0',
              width: '100%'
          }}>
            <div style={{
              padding: '16px 24px',
              borderRadius: '20px',
              borderTopRightRadius: msg.role === 'user' ? '4px' : '20px',
              borderTopLeftRadius: msg.role === 'model' ? '4px' : '20px',
              backgroundColor: msg.role === 'user' ? 'transparent' : 'rgba(255, 255, 255, 0.03)',
              background: msg.role === 'user' ? 'var(--accent-gradient)' : undefined,
              border: msg.role === 'model' ? '1px solid var(--border-glass)' : 'none',
              color: '#fff',
              lineHeight: '1.6',
              fontSize: '15px',
              boxShadow: msg.role === 'user' ? '0 4px 12px rgba(124, 58, 237, 0.3)' : 'none',
              backdropFilter: msg.role === 'model' ? 'blur(10px)' : 'none',
            }}>
              {msg.content}
            </div>
            
            {/* Model Metadata */}
            {msg.role === 'model' && msg.sources && (
              <div style={{ marginTop: '8px', marginLeft: '4px' }}>
                <details style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  <summary style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', listStyle: 'none' }}>
                    <span style={{ fontWeight: 500 }}>{msg.sources.length} References</span>
                    <IconChevronDown />
                  </summary>
                  <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {msg.sources.map((s, i) => (
                        <div key={i} style={{ padding: '6px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', border: '1px solid var(--border-glass)' }}>{s}</div>
                    ))}
                  </div>
                </details>
              </div>
            )}
          </div>
        ))}
        {loading && (
             <div style={{ display: 'flex', gap: '8px', padding: '0 32px', alignItems: 'center' }}>
                <div className="animate-spin" style={{ width: '18px', height: '18px', border: '2px solid var(--accent-primary)', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Analyzing Knowledge Graph...</span>
             </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input Area */}
      <div style={{ padding: '32px', width: '100%', maxWidth: '900px', margin: '0 auto' }}>
        <div style={{ position: 'relative' }}>
          <input 
            className="glass-input"
            style={{ width: '100%', padding: '16px 24px', paddingRight: '100px', fontSize: '15px', borderRadius: '99px' }}
            placeholder="Ask a question about your data..." 
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
          />
          <button 
            onClick={handleSend}
            className="btn-primary"
            style={{ position: 'absolute', right: '6px', top: '6px', bottom: '6px', padding: '0 20px' }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

// 2. Knowledge Base View
const KnowledgeBaseView = () => {
  const [history, setHistory] = useState<IngestionRecord[]>([]);
  const [isIngesting, setIsIngesting] = useState(false);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Fetch stats on mount
    api.getStats().then(setStats).catch(console.error);
  }, []);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsIngesting(true);
    try {
      const result = await api.ingest(file);
      const record: IngestionRecord = {
        document_id: result.document_id,
        filename: result.filename,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        num_entities: result.num_entities || 0,
        num_relationships: result.num_relationships || 0,
      };
      setHistory(prev => [record, ...prev]);
      
      // Refresh stats
      const updatedStats = await api.getStats();
      setStats(updatedStats);
    } catch (e) {
      console.error("Ingestion error:", e);
      alert(`Ingestion failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setIsIngesting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div style={{ padding: '48px', maxWidth: '1200px', margin: '0 auto', width: '100%', overflowY: 'auto' }}>
      <div style={{ marginBottom: '40px' }}>
          <h1 style={{ fontSize: '28px', fontWeight: 700, margin: '0 0 8px 0' }}>Knowledge Base</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Manage documents and visualize ingestion metrics.</p>
      </div>

      {/* Stats Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '40px' }}>
          <div className="glass-card">
              <div style={{ color: 'var(--text-secondary)', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>Total Entities</div>
              <div style={{ fontSize: '36px', fontWeight: 700, color: '#fff' }}>{stats?.total_entities?.toLocaleString() || '0'}</div>
          </div>
          <div className="glass-card">
              <div style={{ color: 'var(--text-secondary)', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>Total Relationships</div>
              <div style={{ fontSize: '36px', fontWeight: 700, color: '#fff' }}>{stats?.total_relationships?.toLocaleString() || '0'}</div>
          </div>
      </div>

      {/* Hidden File Input */}
      <input 
        ref={fileInputRef}
        type="file" 
        accept=".txt,.md" 
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />

      {/* Upload Zone */}
      <div 
        onClick={() => !isIngesting && fileInputRef.current?.click()}
        style={{ 
          border: '1px dashed rgba(124, 58, 237, 0.4)', 
          borderRadius: '16px', 
          padding: '64px', 
          textAlign: 'center',
          backgroundColor: 'rgba(124, 58, 237, 0.03)',
          cursor: 'pointer',
          marginBottom: '40px',
          transition: 'all 0.3s ease',
        }}
        onMouseOver={(e) => e.currentTarget.style.backgroundColor = 'rgba(124, 58, 237, 0.08)'}
        onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'rgba(124, 58, 237, 0.03)'}
      >
        {isIngesting ? (
           <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
             <div className="animate-spin" style={{ width: '32px', height: '32px', border: '3px solid var(--accent-primary)', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
             <div style={{ color: 'var(--text-primary)' }}>Ingesting Document...</div>
           </div>
        ) : (
          <>
            <div style={{ color: 'var(--accent-primary)', marginBottom: '16px' }}><IconUpload /></div>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '18px', fontWeight: 600 }}>Click to Upload</h3>
            <p style={{ margin: 0, fontSize: '14px', color: 'var(--text-secondary)' }}>Supports PDF, TXT, MD</p>
          </>
        )}
      </div>

      {/* History List */}
      <h3 style={{ fontSize: '16px', marginBottom: '20px' }}>Recent Activity</h3>
      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-glass)', textAlign: 'left', color: 'var(--text-secondary)' }}>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Filename</th>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Time</th>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Entities</th>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr><td colSpan={4} style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>No ingestion history found.</td></tr>
            ) : (
              history.map(rec => (
                <tr key={rec.document_id} style={{ borderBottom: '1px solid var(--border-glass)' }}>
                  <td style={{ padding: '16px 24px', fontWeight: 500 }}>{rec.filename}</td>
                  <td style={{ padding: '16px 24px', color: 'var(--text-secondary)' }}>{rec.timestamp}</td>
                  <td style={{ padding: '16px 24px' }}>{rec.num_entities}</td>
                  <td style={{ padding: '16px 24px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--success)', background: 'rgba(16, 185, 129, 0.1)', padding: '4px 8px', borderRadius: '4px' }}>
                          <IconCheck /> Indexed
                      </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// 3. Graph Explorer View
const GraphExplorerView = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // "Blueprint" Style Graph Config
    const nodes = Array.from({ length: 40 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      radius: Math.random() * 3 + 2,
    }));

    const edges = Array.from({ length: 60 }, () => ({
      source: Math.floor(Math.random() * nodes.length),
      target: Math.floor(Math.random() * nodes.length)
    }));

    let animationId: number;
    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Update
      nodes.forEach(n => {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
        if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
      });

      // Draw Edges (Tech Line Style)
      ctx.strokeStyle = 'rgba(124, 58, 237, 0.15)'; // Violet Low Opacity
      ctx.lineWidth = 1;
      edges.forEach(e => {
        const s = nodes[e.source];
        const t = nodes[e.target];
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(t.x, t.y);
        ctx.stroke();
      });

      // Draw Nodes (Glowing Dots)
      nodes.forEach(n => {
        ctx.fillStyle = '#7c3aed';
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fill();
        // Glow
        ctx.shadowBlur = 10;
        ctx.shadowColor = '#7c3aed';
      });
      ctx.shadowBlur = 0;

      animationId = requestAnimationFrame(render);
    };
    render();
    return () => cancelAnimationFrame(animationId);
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const result = await api.searchEntities(searchQuery, 10);
      setSearchResults(result.entities || []);
    } catch (e) {
      console.error("Search error:", e);
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      {/* Search Overlay */}
      <div style={{ position: 'absolute', top: '32px', left: '50%', transform: 'translateX(-50%)', zIndex: 20, width: '400px' }}>
          <div style={{ position: 'relative' }}>
            <input 
                className="glass-input" 
                placeholder="Search entities..." 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                style={{ width: '100%', paddingLeft: '44px', background: 'rgba(14, 17, 23, 0.8)', backdropFilter: 'blur(8px)' }}
            />
            <div style={{ position: 'absolute', left: '14px', top: '12px', color: 'var(--text-secondary)' }}><IconSearch /></div>
          </div>
          {searchResults.length > 0 && (
            <div style={{ marginTop: '8px', background: 'rgba(14, 17, 23, 0.95)', backdropFilter: 'blur(8px)', borderRadius: '12px', padding: '8px', maxHeight: '300px', overflowY: 'auto' }}>
              {searchResults.map((entity, idx) => (
                <div key={idx} style={{ padding: '8px 12px', borderBottom: idx < searchResults.length - 1 ? '1px solid var(--border-glass)' : 'none' }}>
                  <div style={{ fontWeight: 600, fontSize: '14px' }}>{entity.name}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{entity.type}</div>
                  {entity.description && <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>{entity.description}</div>}
                </div>
              ))}
            </div>
          )}
      </div>

      {/* Full Screen Canvas */}
      <div style={{ flex: 1, backgroundColor: '#0b0d11', backgroundImage: 'radial-gradient(#1a1d26 1px, transparent 1px)', backgroundSize: '40px 40px' }}>
          <canvas ref={canvasRef} width={1400} height={900} style={{ width: '100%', height: '100%', display: 'block' }} />
      </div>
      
      <div style={{ position: 'absolute', bottom: '24px', right: '24px', fontSize: '12px', color: 'var(--text-secondary)', pointerEvents: 'none' }}>
          GRAPH ENGINE V2.0 • LIVE
      </div>
    </div>
  );
};

// --- Main App Layout ---

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

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);
root.render(<App />);