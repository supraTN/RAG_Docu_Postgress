"use client";

import { motion } from "framer-motion";
import { FileText, Layers, Box, FlaskConical } from "lucide-react";
import { EVAL_METRICS, PROJECT_STATS, METRIC_EXPLANATIONS } from "@/app/lib/constants";
import MetricBar from "./MetricBar";
import AnimatedCounter from "./AnimatedCounter";

const statIcons = [FileText, Layers, Box, FlaskConical];

interface MetricCardProps {
  label: string;
  count: number;
  retrieval: Record<string, number>;
  generation: Record<string, number>;
  delay: number;
}

function MetricCard({
  label,
  count,
  retrieval,
  generation,
  delay,
}: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800"
    >
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">{label}</h3>
        <span className="text-xs font-mono text-zinc-500 bg-zinc-800 px-2.5 py-1 rounded-lg">
          {count} questions
        </span>
      </div>

      {/* Retrieval */}
      <div className="mb-6">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
          Retrieval
        </p>
        <div className="space-y-4">
          {Object.entries(retrieval).map(([key, val], i) => (
            <MetricBar
              key={key}
              label={key}
              value={val}
              delay={i * 0.08}
              explanation={METRIC_EXPLANATIONS[key]}
            />
          ))}
        </div>
      </div>

      {/* Generation */}
      <div>
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
          Generation
        </p>
        <div className="space-y-4">
          {Object.entries(generation).map(([key, val], i) => (
            <MetricBar
              key={key}
              label={key}
              value={val}
              delay={i * 0.08}
              explanation={METRIC_EXPLANATIONS[key]}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

export default function MetricsSection() {
  return (
    <section id="metrics" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        {/* Heading */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Résultats d&apos;Évaluation
          </h2>
          <p className="text-zinc-400 max-w-2xl mx-auto">
            Le pipeline RAG indexe la documentation complète de PostgreSQL 16 et
            est évalué sur{" "}
            <span className="text-white font-semibold">79 questions réelles</span>{" "}
            couvrant des formulations naturelles et techniques.
          </p>
        </motion.div>

        {/* Project stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-16">
          {PROJECT_STATS.map((stat, i) => {
            const Icon = statIcons[i];
            return (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800 text-center"
              >
                <Icon className="w-5 h-5 text-blue-400 mx-auto mb-3" />
                <p className="text-2xl sm:text-3xl font-bold text-white mb-1">
                  {stat.value}
                </p>
                <p className="text-sm font-semibold text-zinc-300 mb-1">
                  {stat.label}
                </p>
                <p className="text-[11px] text-zinc-600 leading-snug">
                  {stat.description}
                </p>
              </motion.div>
            );
          })}
        </div>

        {/* Why these scores matter */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="mb-12 p-5 rounded-2xl bg-blue-600/5 border border-blue-500/10 text-center"
        >
          <p className="text-sm text-zinc-400 leading-relaxed max-w-3xl mx-auto">
            <span className="text-blue-400 font-semibold">Pourquoi ces scores comptent :</span>{" "}
            un Hit Rate @3 de 100% signifie que sur 6 203 chunks possibles, le bon
            document est <span className="text-white">toujours</span> dans le top 3.
            Une Correctness de 99.6% montre que le LLM génère des réponses fiables
            sans halluciner à partir des sources récupérées.
          </p>
        </motion.div>

        {/* Metric cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <MetricCard {...EVAL_METRICS.userStyle} delay={0} />
          <MetricCard {...EVAL_METRICS.technical} delay={0.15} />
        </div>
      </div>
    </section>
  );
}
