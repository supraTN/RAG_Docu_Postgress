"use client";

import { motion } from "framer-motion";
import {
  MessageSquare,
  Cpu,
  Database,
  ArrowUpDown,
  Filter,
  Sparkles,
  ChevronRight,
} from "lucide-react";

const ICONS = {
  MessageSquare,
  Cpu,
  Database,
  ArrowUpDown,
  Filter,
  Sparkles,
} as const;

interface PipelineStepProps {
  label: string;
  icon: keyof typeof ICONS;
  description: string;
  index: number;
  isLast: boolean;
}

export default function PipelineStep({
  label,
  icon,
  description,
  index,
  isLast,
}: PipelineStepProps) {
  const Icon = ICONS[icon];

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, delay: index * 0.12 }}
        className="flex flex-col items-center gap-3 min-w-[120px]"
      >
        <div className="relative">
          <div className="absolute inset-0 blur-xl bg-blue-600/10 rounded-full" />
          <div className="relative flex items-center justify-center w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-800 shadow-lg">
            <Icon className="w-6 h-6 text-blue-400" />
          </div>
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-white">{label}</p>
          <p className="text-xs text-zinc-500 mt-0.5">{description}</p>
        </div>
      </motion.div>

      {!isLast && (
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.3, delay: index * 0.12 + 0.1 }}
          className="hidden md:flex items-center pt-1"
        >
          <ChevronRight className="w-5 h-5 text-zinc-700" />
        </motion.div>
      )}
    </>
  );
}
