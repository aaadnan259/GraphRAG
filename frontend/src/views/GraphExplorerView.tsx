import React, { useState, useEffect, useRef } from "react";
import { EntityResult } from "@/types";
import { api } from "@/services/api";
import { IconSearch } from "@/components/Icons";

export const GraphExplorerView = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<EntityResult[]>([]);

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
