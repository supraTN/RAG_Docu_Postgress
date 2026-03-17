"use client";

import { motion } from "framer-motion";
import { Search, Brain } from "lucide-react";

const cards = [
  {
    icon: Search,
    title: "Retrieval",
    subtitle: "Embedding + Reranking",
    description:
      "Chaque question a un chunk source connu. On vérifie si le pipeline retrieval (pgvector + Cohere Rerank) le retrouve dans le top-k, avec Hit Rate et MRR.",
  },
  {
    icon: Brain,
    title: "Generation",
    subtitle: "LLM-as-Judge",
    description:
      "Un LLM évalue la fidélité, la justesse et la complétude de chaque réponse par rapport à la vérité terrain.",
  },
];

export default function MethodologySection() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Méthodologie
          </h2>
          <p className="text-zinc-400 max-w-xl mx-auto">
            Évaluation sans biais circulaire : les questions de test sont
            générées directement depuis les chunks, pas depuis le retriever.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {cards.map((c, i) => (
            <motion.div
              key={c.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.12 }}
              className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600/10">
                  <c.icon className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">
                    {c.title}
                  </h3>
                  <p className="text-xs text-zinc-500">{c.subtitle}</p>
                </div>
              </div>
              <p className="text-sm text-zinc-400 leading-relaxed">
                {c.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
