import React, { useState, useEffect, useRef } from "react";
import { Message } from "@/types";
import { api } from "@/services/api";
import { IconChevronDown } from "@/components/Icons";

export const ChatView = () => {
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
