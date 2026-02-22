export interface Message {
  role: "user" | "model";
  content: string;
  sources?: string[];
  isGraphAugmented?: boolean;
}

export interface IngestionRecord {
  document_id: string;
  filename: string;
  timestamp: string;
  num_entities: number;
  num_relationships: number;
}

export interface GraphStats {
  total_entities: number;
  total_relationships: number;
  entity_types: Record<string, number>;
  relationship_types: Record<string, number>;
}

export interface QueryResponse {
  answer: string;
  vector_context: string[];
  graph_context: string;
  sources: string[];
}

export interface IngestResponse {
  success: boolean;
  document_id: string;
  filename: string;
  num_chunks?: number;
  num_entities?: number;
  num_relationships?: number;
  error?: string;
}

export interface EntityResult {
  name: string;
  type: string;
  description?: string;
}

export interface SearchEntitiesResponse {
  entities: EntityResult[];
}
