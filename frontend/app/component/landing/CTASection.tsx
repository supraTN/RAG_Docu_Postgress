"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import Link from "next/link";

export default function CTASection() {
  return (
    <section className="py-24 px-6">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="max-w-3xl mx-auto text-center"
      >
        <div className="relative p-12 rounded-3xl bg-zinc-900/50 border border-zinc-800 overflow-hidden">
          {/* Gradient glow */}
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-purple-600/5 pointer-events-none" />

          <div className="relative z-10">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Prêt à essayer ?
            </h2>
            <p className="text-zinc-400 mb-8 max-w-md mx-auto">
              Posez n&apos;importe quelle question sur PostgreSQL 16 et obtenez
              une réponse sourcée en temps réel.
            </p>
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-2xl transition-all duration-200 hover:scale-[1.03] active:scale-95 shadow-lg shadow-blue-600/25"
            >
              Ouvrir le Chat
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>

        <p className="mt-8 text-xs text-zinc-600">
          Built with Next.js, FastAPI, pgvector & OpenAI
        </p>
      </motion.div>
    </section>
  );
}
