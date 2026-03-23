export const EVAL_METRICS = {
  userStyle: {
    label: "Questions type utilisateur",
    count: 40,
    retrieval: {
      "Hit Rate @1": 0.875,
      "Hit Rate @3": 1.0,
      "Hit Rate @5": 1.0,
      MRR: 0.9375,
    },
    generation: {
      Faithfulness: 0.9328,
      Correctness: 1.0,
      Completeness: 1.0,
    },
  },
  technical: {
    label: "Questions techniques",
    count: 39,
    retrieval: {
      "Hit Rate @1": 1.0,
      "Hit Rate @3": 1.0,
      "Hit Rate @5": 1.0,
      MRR: 1.0,
    },
    generation: {
      Faithfulness: 0.9374,
      Correctness: 0.9923,
      Completeness: 0.9923,
    },
  },
};

export const PIPELINE_STEPS = [
  {
    label: "Query",
    icon: "MessageSquare" as const,
    description: "Question de l'utilisateur",
  },
  {
    label: "Embed",
    icon: "Cpu" as const,
    description: "text-embedding-3-large",
  },
  {
    label: "Retrieve",
    icon: "Database" as const,
    description: "pgvector cosine top-20",
  },
  {
    label: "Rerank",
    icon: "ArrowUpDown" as const,
    description: "Cohere Rerank v4",
  },
  {
    label: "Filter",
    icon: "Filter" as const,
    description: "Ratio de score adaptatif",
  },
  {
    label: "Generate",
    icon: "Sparkles" as const,
    description: "GPT-5-mini streaming",
  },
];

export const TECH_STACK = [
  { name: "Next.js 16", category: "Frontend", color: "text-white" },
  { name: "React 19", category: "Frontend", color: "text-blue-400" },
  { name: "FastAPI", category: "Backend", color: "text-emerald-400" },
  { name: "PostgreSQL 16", category: "Database", color: "text-blue-400" },
  { name: "pgvector", category: "Vector Store", color: "text-purple-400" },
  { name: "OpenAI", category: "LLM & Embeddings", color: "text-emerald-400" },
  { name: "Cohere Rerank", category: "Reranking", color: "text-orange-400" },
  { name: "Docker", category: "Infrastructure", color: "text-blue-400" },
];

export const PROJECT_STATS = [
  { value: "1 149", label: "Pages HTML", description: "Documentation PostgreSQL 16 complète" },
  { value: "6 203", label: "Chunks", description: "Découpage intelligent (400 tokens, 80 overlap)" },
  { value: "3 072", label: "Dimensions", description: "Vecteurs text-embedding-3-large" },
  { value: "79", label: "Questions de test", description: "40 user-style + 39 techniques" },
];

export const METRIC_EXPLANATIONS: Record<string, string> = {
  "Hit Rate @1":
    "Le bon chunk est-il en 1re position ? Un score élevé signifie que le système trouve directement la bonne réponse.",
  "Hit Rate @3":
    "Le bon chunk est-il dans le top 3 ? 100% = le système ne rate jamais la bonne source dans ses 3 meilleurs résultats.",
  "Hit Rate @5":
    "Le bon chunk est-il dans le top 5 ? Score de filet de sécurité — ici 100% sur les deux jeux de test.",
  MRR:
    "Mean Reciprocal Rank — plus le bon chunk est haut dans le classement, plus le score est proche de 1.0.",
  Faithfulness:
    "La réponse est-elle fidèle aux chunks récupérés ? Mesure l'absence d'hallucination.",
  Correctness:
    "La réponse répond-elle correctement à la question ? Évalué par un LLM-as-judge.",
  Completeness:
    "La réponse couvre-t-elle tous les points clés ? Vérifie qu'aucune information importante n'est omise.",
};

export const HIGHLIGHTS = [
  {
    title: "Récupération en deux étapes",
    description:
      "Recherche par similarité vectorielle suivie d'un reclassement neuronal pour plus de précision.",
  },
  {
    title: "Filtrage Adaptatif",
    description:
      "Seuils de score dynamiques qui s'adaptent automatiquement à la difficulté de la requête.",
  },
  {
    title: "Streaming SSE",
    description:
      "Streaming de la réponse token par token en temps réel pour un retour instantané.",
  },
  {
    title: "Évaluation sans Biais",
    description:
      "La vérité terrain est générée depuis les chunks, pas depuis le retriever lui-même.",
  },
];
