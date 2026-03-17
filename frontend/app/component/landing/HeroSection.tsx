"use client";

import { motion } from "framer-motion";
import { Database, ArrowRight, ChevronDown } from "lucide-react";
import Link from "next/link";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.15 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export default function HeroSection() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 text-center overflow-hidden">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="relative z-10 flex flex-col items-center"
      >
        {/* Icon */}
        <motion.div variants={item} className="relative mb-8">
          <div className="absolute inset-0 blur-3xl bg-blue-600/20 rounded-full scale-150" />
          <div className="relative flex items-center justify-center w-24 h-24 rounded-3xl bg-zinc-900 border border-zinc-800 shadow-2xl">
            <Database className="w-12 h-12 text-blue-500" />
          </div>
        </motion.div>

        {/* Status badge */}
        <motion.div
          variants={item}
          className="flex items-center gap-2 mb-6 px-4 py-2 rounded-full bg-zinc-900/80 border border-zinc-800"
        >
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-semibold text-emerald-500/80 tracking-wide uppercase">
            RAG System Active
          </span>
        </motion.div>

        {/* Title */}
        <motion.h1
          variants={item}
          className="text-5xl sm:text-7xl font-bold tracking-tight text-white mb-4"
        >
          PostgreSQL{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-600">
            RAG Assistant
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          variants={item}
          className="text-lg sm:text-xl text-zinc-400 max-w-2xl mb-10 leading-relaxed"
        >
          Un assistant intelligent de documentation PostgreSQL propulsé par un
          pipeline RAG complet : embeddings vectoriels, reranking neural et
          génération en streaming.
        </motion.p>

        {/* CTAs */}
        <motion.div variants={item} className="flex flex-wrap gap-4 justify-center">
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-2xl transition-all duration-200 hover:scale-[1.03] active:scale-95 shadow-lg shadow-blue-600/25"
          >
            Essayer le Chat
            <ArrowRight className="w-5 h-5" />
          </Link>
          <a
            href="#metrics"
            className="inline-flex items-center gap-2 px-8 py-4 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white font-semibold rounded-2xl border border-zinc-800 hover:border-zinc-700 transition-all duration-200"
          >
            Voir les Résultats
            <ChevronDown className="w-5 h-5" />
          </a>
        </motion.div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
        >
          <ChevronDown className="w-6 h-6 text-zinc-600" />
        </motion.div>
      </motion.div>
    </section>
  );
}
