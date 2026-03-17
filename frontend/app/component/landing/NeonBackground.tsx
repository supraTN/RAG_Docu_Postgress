"use client";

import { motion } from "framer-motion";

const particles = [
  { id: 0, top: "12%", left: "8%", drift: -45, duration: 7, delay: 0 },
  { id: 1, top: "25%", left: "22%", drift: -55, duration: 9, delay: 1.2 },
  { id: 2, top: "18%", left: "45%", drift: -35, duration: 6, delay: 3.5 },
  { id: 3, top: "40%", left: "70%", drift: -60, duration: 8, delay: 0.8 },
  { id: 4, top: "55%", left: "15%", drift: -40, duration: 5, delay: 4.2 },
  { id: 5, top: "35%", left: "88%", drift: -50, duration: 7.5, delay: 2.1 },
  { id: 6, top: "65%", left: "35%", drift: -45, duration: 6.5, delay: 5.8 },
  { id: 7, top: "78%", left: "60%", drift: -55, duration: 8.5, delay: 1.5 },
  { id: 8, top: "48%", left: "92%", drift: -38, duration: 9.5, delay: 3.0 },
  { id: 9, top: "82%", left: "25%", drift: -52, duration: 7.2, delay: 6.5 },
  { id: 10, top: "20%", left: "75%", drift: -42, duration: 5.8, delay: 2.8 },
  { id: 11, top: "70%", left: "50%", drift: -48, duration: 8.2, delay: 4.8 },
  { id: 12, top: "30%", left: "12%", drift: -58, duration: 6.8, delay: 7.2 },
  { id: 13, top: "88%", left: "80%", drift: -35, duration: 9.0, delay: 0.5 },
  { id: 14, top: "15%", left: "58%", drift: -65, duration: 7.8, delay: 5.0 },
  { id: 15, top: "60%", left: "5%", drift: -40, duration: 6.2, delay: 3.8 },
  { id: 16, top: "45%", left: "40%", drift: -50, duration: 8.8, delay: 1.8 },
  { id: 17, top: "75%", left: "72%", drift: -44, duration: 5.5, delay: 6.0 },
  { id: 18, top: "50%", left: "28%", drift: -56, duration: 7.4, delay: 2.5 },
  { id: 19, top: "85%", left: "48%", drift: -42, duration: 9.2, delay: 4.0 },
];

const orbs = [
  // Large slow-moving blue orb — top left
  {
    className: "w-[500px] h-[500px] bg-blue-600/15",
    initial: { x: "-10%", y: "-5%" },
    animate: { x: ["−10%", "5%", "-10%"], y: ["-5%", "10%", "-5%"] },
    duration: 20,
    top: "5%",
    left: "10%",
  },
  // Purple orb — mid right
  {
    className: "w-[400px] h-[400px] bg-purple-600/12",
    initial: { x: "10%", y: "0%" },
    animate: { x: ["10%", "-8%", "10%"], y: ["0%", "15%", "0%"] },
    duration: 25,
    top: "30%",
    right: "5%",
  },
  // Cyan accent — bottom left
  {
    className: "w-[350px] h-[350px] bg-cyan-500/10",
    initial: { x: "0%", y: "0%" },
    animate: { x: ["0%", "12%", "0%"], y: ["0%", "-10%", "0%"] },
    duration: 22,
    bottom: "15%",
    left: "5%",
  },
  // Small blue — center, slow pulse
  {
    className: "w-[300px] h-[300px] bg-blue-500/10",
    initial: { x: "0%", y: "0%" },
    animate: { x: ["0%", "-6%", "0%"], y: ["0%", "8%", "0%"] },
    duration: 18,
    top: "55%",
    left: "40%",
  },
  // Deep purple — bottom right
  {
    className: "w-[450px] h-[450px] bg-indigo-600/10",
    initial: { x: "0%", y: "0%" },
    animate: { x: ["0%", "-10%", "0%"], y: ["0%", "-12%", "0%"] },
    duration: 28,
    bottom: "5%",
    right: "10%",
  },
];

export default function NeonBackground() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {/* Grid overlay */}
      <div className="neon-grid absolute inset-0 opacity-[0.03]" />

      {/* Floating orbs */}
      {orbs.map((orb, i) => (
        <motion.div
          key={i}
          className={`absolute rounded-full blur-[100px] ${orb.className}`}
          style={{
            top: orb.top,
            left: orb.left,
            right: orb.right,
            bottom: orb.bottom,
          }}
          initial={orb.initial}
          animate={orb.animate}
          transition={{
            duration: orb.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}

      {/* Horizontal neon line accents */}
      <motion.div
        className="absolute top-[20%] left-0 w-full h-px"
        style={{
          background:
            "linear-gradient(90deg, transparent, rgba(59,130,246,0.08) 30%, rgba(139,92,246,0.06) 70%, transparent)",
        }}
        animate={{ opacity: [0.3, 0.7, 0.3] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-[50%] left-0 w-full h-px"
        style={{
          background:
            "linear-gradient(90deg, transparent, rgba(6,182,212,0.06) 40%, rgba(59,130,246,0.08) 60%, transparent)",
        }}
        animate={{ opacity: [0.2, 0.5, 0.2] }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 3,
        }}
      />
      <motion.div
        className="absolute top-[80%] left-0 w-full h-px"
        style={{
          background:
            "linear-gradient(90deg, transparent, rgba(139,92,246,0.07) 25%, rgba(59,130,246,0.05) 75%, transparent)",
        }}
        animate={{ opacity: [0.2, 0.6, 0.2] }}
        transition={{
          duration: 12,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 5,
        }}
      />

      {/* Floating particles — deterministic positions to avoid hydration mismatch */}
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute w-1 h-1 rounded-full bg-blue-400/30"
          style={{ top: p.top, left: p.left }}
          animate={{ y: [0, p.drift, 0], opacity: [0, 0.6, 0] }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            ease: "easeInOut",
            delay: p.delay,
          }}
        />
      ))}
    </div>
  );
}
