"use client";

import { motion } from "framer-motion";
import { Database, MessageSquare } from "lucide-react";
import { SUGGESTED_QUESTIONS } from "@/app/types";

interface WelcomeScreenProps {
  onSelect: (question: string) => void;
}

export default function WelcomeScreen({ onSelect }: WelcomeScreenProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center min-h-[70vh] px-6 text-center"
    >
      <div className="relative mb-8">
        <div className="absolute inset-0 blur-3xl bg-blue-600/20 rounded-full" />
        <div className="relative flex items-center justify-center w-24 h-24 rounded-3xl bg-zinc-900 border border-zinc-800 shadow-2xl">
          <Database className="w-12 h-12 text-blue-500" />
        </div>
      </div>

      <h2 className="text-3xl font-bold tracking-tight text-white mb-3">
        PostgreSQL <span className="text-blue-500">Docs Assistant</span>
      </h2>
      <p className="text-zinc-400 max-w-lg mb-12 text-lg leading-relaxed">
        L&apos;intelligence artificielle au service de votre base de donnÃ©es.
        Posez vos questions sur la documentation officielle.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-3xl">
        {SUGGESTED_QUESTIONS.map((q, idx) => (
          <motion.button
            key={q}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            onClick={() => onSelect(q)}
            className="flex items-start gap-4 p-4 text-left rounded-2xl bg-zinc-900/50 hover:bg-zinc-800/80 border border-zinc-800 hover:border-zinc-700 transition-all duration-200 group"
          >
            <div className="mt-1 shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-zinc-800 group-hover:bg-blue-600/20 group-hover:text-blue-400 transition-colors">
              <MessageSquare className="w-4 h-4" />
            </div>
            <span className="text-sm font-medium text-zinc-300 group-hover:text-white">
              {q}
            </span>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
