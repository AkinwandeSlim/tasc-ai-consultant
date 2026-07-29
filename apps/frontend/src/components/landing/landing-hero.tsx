"use client";

import { motion } from "framer-motion";
import {
  Brain,
  BarChart3,
  Target,
  Cpu,
  Lightbulb,
  Clock,
  Wifi,
  ArrowRight,
  FlaskConical,
} from "lucide-react";
import KineticGrid from "@/components/landing/kinetic-grid";

interface LandingHeroProps {
  isConnected: boolean;
  isSimulationMode: boolean;
  backendVersion: string;
  onStart: () => void;
  isStarting: boolean;
}

const FEATURES = [
  {
    icon: Brain,
    title: "AI Consultation",
    description: "Intelligent conversation that understands your business",
  },
  {
    icon: BarChart3,
    title: "Business Intelligence",
    description: "Real-time analysis of your business context",
  },
  {
    icon: Target,
    title: "Lead Qualification",
    description: "Deterministic scoring with transparent criteria",
  },
  {
    icon: Cpu,
    title: "Automation Readiness",
    description: "Assessment of AI & automation opportunities",
  },
  {
    icon: Lightbulb,
    title: "Smart Recommendations",
    description: "Ranked services matched to your needs",
  },
];

export function LandingHero({
  isConnected,
  isSimulationMode,
  onStart,
  isStarting,
}: LandingHeroProps) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-surface-base px-4">
      {/* ── Interactive kinetic grid background ── */}
      <KineticGrid
        background="transparent"
        dotColor="#13135F"
        lineColor="#13135F"
        trailColor="#2563EB"
        spacing={45}
        radius={350}
        strength={4}
        trail={true}
      />

      {/* ── Content ── */}
      <div className="relative z-10 mx-auto max-w-3xl text-center">
        {/* Badges */}
        <div className="mb-6 flex items-center justify-center gap-3">
          {isSimulationMode && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-body-xs font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
              <FlaskConical className="size-3" />
              Simulation Mode
            </span>
          )}
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-body-xs font-medium ${
              isConnected
                ? "border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300"
                : "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
            }`}
          >
            <Wifi
              className={`size-3 ${isConnected ? "" : "animate-pulse"}`}
            />
            {isConnected ? "Backend Connected" : "Connecting..."}
          </span>
        </div>

        {/* Title */}
        <motion.h1
          className="text-heading-lg font-bold tracking-tight sm:text-5xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          Enterprise AI
          <br />
          Consultation Platform
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          className="mt-4 text-body text-muted-foreground max-w-xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          Discover automation opportunities, assess AI readiness, and receive
          intelligent implementation recommendations.
        </motion.p>

        {/* Estimate */}
        <motion.div
          className="mt-4 flex items-center justify-center gap-2 text-body-sm text-muted-foreground"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Clock className="size-4" />
          <span>Estimated consultation time: 4–6 minutes</span>
        </motion.div>

        {/* CTA */}
        <motion.div
          className="mt-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <button
            onClick={onStart}
            disabled={!isConnected || isStarting}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-8 py-3.5 text-body font-medium text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:opacity-90 hover:shadow-xl hover:shadow-primary/30 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isStarting ? (
              <>
                <span className="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                Starting...
              </>
            ) : (
              <>
                Start AI Consultation
                <ArrowRight className="size-4" />
              </>
            )}
          </button>
        </motion.div>

        {/* Feature Cards */}
        <motion.div
          className="mt-12 grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="rounded-xl border border-border bg-surface-raised p-4 text-left transition-shadow hover:shadow-sm"
            >
              <feature.icon className="mb-2 size-5 text-primary" />
              <p className="text-body-sm font-medium">{feature.title}</p>
              <p className="mt-0.5 text-body-xs text-muted-foreground">
                {feature.description}
              </p>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}