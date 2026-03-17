"use client";

import { motion } from "framer-motion";
import AnimatedCounter from "./AnimatedCounter";
import { cn } from "@/app/lib/utils";

interface MetricBarProps {
  label: string;
  value: number; // 0-1
  delay?: number;
  explanation?: string;
}

function getBarColor(value: number) {
  if (value >= 0.95) return "bg-emerald-500";
  if (value >= 0.9) return "bg-blue-500";
  return "bg-amber-500";
}

export default function MetricBar({
  label,
  value,
  delay = 0,
  explanation,
}: MetricBarProps) {
  const pct = value * 100;
  const isPerfect = value >= 0.999;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-400">{label}</span>
        <span className="flex items-center gap-2 font-mono text-white">
          <AnimatedCounter target={pct} />
          {isPerfect && (
            <span className="text-[10px] font-semibold tracking-wider text-emerald-400 bg-emerald-400/10 px-1.5 py-0.5 rounded">
              PERFECT
            </span>
          )}
        </span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <motion.div
          className={cn("h-full rounded-full", getBarColor(value))}
          initial={{ width: 0 }}
          whileInView={{ width: `${pct}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: "easeOut", delay }}
        />
      </div>
      {explanation && (
        <p className="text-[11px] text-zinc-600 leading-relaxed">
          {explanation}
        </p>
      )}
    </div>
  );
}
