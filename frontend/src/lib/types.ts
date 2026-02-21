/**
 * TypeScript interfaces mirroring backend schemas.
 *
 * See: docs/architecture/LLD_pipeline.md § 7
 */

export interface AnalyzeResponse {
  analysis_id: string;
  ticker: string;
  status: string;
  sse_url: string;
}

export interface ScoreBreakdown {
  impact: number;
  feasibility: number;
  risk_adjusted_return: number;
  strategic_alignment: number;
}

export interface MoveDocument {
  move_id: string;
  agent_id: string;
  persona: string;
  risk_level: "low" | "medium" | "high";
  title: string;
  content: string;
  ticker: string;
}

export interface MoveResult {
  move_id: string;
  total_score: number;
  scores_by_agent: Record<string, ScoreBreakdown>;
  move_document: MoveDocument;
}

export interface ConversationLog {
  move_id: string;
  i1: ConversationEntry[];
  i2: ConversationEntry[];
  i3: ConversationEntry[];
}

export interface ConversationEntry {
  role: string;
  content: string;
  round: number;
}

export interface AnalysisResult {
  recommended_moves: MoveResult[];
  other_moves: MoveResult[];
  f1: string;
  f2: string;
  conversation_logs: ConversationLog[];
}

export interface AnalysisStatus {
  analysis_id: string;
  ticker: string;
  status: "running" | "complete" | "error";
  result: AnalysisResult | null;
}
