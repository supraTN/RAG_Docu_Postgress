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
  "Comment les index améliorent-ils les performances des requêtes ?",
  "Qu'est-ce que le MVCC dans PostgreSQL ?",
  "Comment écrire des CTE efficaces ?",
  "Quelle est la différence entre INNER JOIN et LEFT JOIN ?",
] as const;
