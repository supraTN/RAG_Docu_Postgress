"use client";

import { useEffect, useRef } from "react";
import {
  useInView,
  useMotionValue,
  useTransform,
  animate,
  motion,
} from "framer-motion";

interface AnimatedCounterProps {
  target: number;
  suffix?: string;
  decimals?: number;
}

export default function AnimatedCounter({
  target,
  suffix = "%",
  decimals = 1,
}: AnimatedCounterProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });
  const motionValue = useMotionValue(0);
  const display = useTransform(motionValue, (v) => v.toFixed(decimals));

  useEffect(() => {
    if (isInView) {
      animate(motionValue, target, { duration: 1.5, ease: "easeOut" });
    }
  }, [isInView, motionValue, target]);

  return (
    <span ref={ref} className="tabular-nums">
      <motion.span>{display}</motion.span>
      {suffix}
    </span>
  );
}
