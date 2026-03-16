export type ModelOption = "gpt-4.1-mini" | "gpt-5-mini";

export type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
  sources?: string[];
  latency?: number;
  timestamp: Date;
};

export const SUGGESTED_QUESTIONS = [
  "How do indexes improve query performance?",
  "What is MVCC in PostgreSQL?",
  "How do I write efficient CTEs?",
  "What is the difference between INNER and LEFT JOIN?",
] as const;
