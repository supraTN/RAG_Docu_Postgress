export type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
  sources?: string[];
  latency?: number;
  timestamp: Date;
};

export const SUGGESTED_QUESTIONS = [
  "Comment les index améliorent-ils les performances ?",
  "Qu'est-ce que le MVCC dans PostgreSQL ?",
  "Comment écrire des CTE efficaces ?",
  "Différences entre INNER et LEFT JOIN ?",
] as const;
