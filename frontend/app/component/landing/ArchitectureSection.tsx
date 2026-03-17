"use client";

import { motion } from "framer-motion";
import { PIPELINE_STEPS, HIGHLIGHTS } from "@/app/lib/constants";
import PipelineStep from "./PipelineStep";
import { Zap } from "lucide-react";

export default function ArchitectureSection() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Heading */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Comment ça marche
          </h2>
          <p className="text-zinc-400 max-w-xl mx-auto">
            Un pipeline RAG en 6 étapes, de la question utilisateur à la réponse
            sourcée.
          </p>
        </motion.div>

        {/* Pipeline */}
        <div className="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-4 mb-20">
          {PIPELINE_STEPS.map((step, i) => (
            <PipelineStep
              key={step.label}
              {...step}
              index={i}
              isLast={i === PIPELINE_STEPS.length - 1}
            />
          ))}
        </div>

        {/* Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-4xl mx-auto">
          {HIGHLIGHTS.map((h, i) => (
            <motion.div
              key={h.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              className="flex items-start gap-4 p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800"
            >
              <div className="shrink-0 mt-0.5 flex items-center justify-center w-9 h-9 rounded-lg bg-blue-600/10">
                <Zap className="w-4 h-4 text-blue-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white mb-1">
                  {h.title}
                </h3>
                <p className="text-xs text-zinc-500 leading-relaxed">
                  {h.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
