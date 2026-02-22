import { IngestResponse, GraphStats, SearchEntitiesResponse, QueryResponse } from "@/types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class APIService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async query(queryText: string, useVector: boolean = true, useGraph: boolean = true): Promise<QueryResponse> {
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

  async ingest(file: File): Promise<IngestResponse> {
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

  async searchEntities(query: string, limit: number = 10): Promise<SearchEntitiesResponse> {
    const response = await fetch(`${this.baseUrl}/search/entities?query=${encodeURIComponent(query)}&limit=${limit}`);

    if (!response.ok) {
      throw new Error(`Entity search failed: ${response.statusText}`);
    }

    return await response.json();
  }
}

export const api = new APIService();
