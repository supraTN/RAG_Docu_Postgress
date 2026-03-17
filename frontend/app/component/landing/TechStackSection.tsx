"use client";

import { motion } from "framer-motion";
import { TECH_STACK } from "@/app/lib/constants";

export default function TechStackSection() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Stack Technique
          </h2>
          <p className="text-zinc-400 max-w-xl mx-auto">
            Technologies modernes pour un pipeline robuste, de l&apos;ingestion
            au rendu.
          </p>
        </motion.div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {TECH_STACK.map((tech, i) => (
            <motion.div
              key={tech.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.35, delay: i * 0.06 }}
              className="group relative p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800 hover:border-zinc-700 transition-colors"
            >
              <div
                className={`absolute top-0 left-4 right-4 h-px ${tech.color.replace("text-", "bg-")} opacity-40`}
              />
              <p className={`text-sm font-semibold ${tech.color} mb-1`}>
                {tech.name}
              </p>
              <p className="text-xs text-zinc-500">{tech.category}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
