import React, { useState, useEffect, useRef } from "react";
import { IngestionRecord, GraphStats } from "@/types";
import { api } from "@/services/api";
import { IconUpload, IconCheck } from "@/components/Icons";

export const KnowledgeBaseView = () => {
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
