"use client";

import NeonBackground from "./NeonBackground";
import HeroSection from "./HeroSection";
import ArchitectureSection from "./ArchitectureSection";
import MetricsSection from "./MetricsSection";
import TechStackSection from "./TechStackSection";
import MethodologySection from "./MethodologySection";
import CTASection from "./CTASection";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen bg-black text-white selection:bg-blue-500/30">
      <NeonBackground />
      <div className="relative z-10">
        <HeroSection />
        <ArchitectureSection />
        <MetricsSection />
        <TechStackSection />
        <MethodologySection />
        <CTASection />
      </div>
    </div>
  );
}
