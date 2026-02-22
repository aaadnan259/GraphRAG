import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "@/services/api";

export const StatusIndicator = () => {
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
    <div className="glass-card status-pod">
      <h4 className="status-title">Server Status</h4>
      <div className="status-list">
        <div className="status-item">
          <div className={`status-dot ${backendStatus ? 'online' : ''}`} />
          FastAPI Backend
        </div>
        <div className="status-item">
          <div className={`status-dot ${backendStatus ? 'online' : ''}`} />
          Neo4j Graph
        </div>
        <div className="status-item">
          <div className={`status-dot ${backendStatus ? 'online' : ''}`} />
          Chroma Vector
        </div>
      </div>
    </div>
  );
};
