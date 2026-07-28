"use client";

import { LandingHero } from "@/components/landing/landing-hero";
import { ConsultationFeature } from "@/features/consultation/components/consultation-feature";
import { useHealthCheck } from "@/hooks/use-health-check";
import { useConsultation } from "@/hooks/use-consultation";
import { useSession } from "@/contexts/session-context";

export default function HomePage() {
  const { health, isConnected } = useHealthCheck();
  const consultation = useConsultation();
  const session = useSession();
  const hasSession = session.sessionId !== null;

  if (hasSession) {
    return (
      <ConsultationFeature
        consultation={consultation}
        health={health}
        isConnected={isConnected}
      />
    );
  }

  return (
    <LandingHero
      isConnected={isConnected}
      isSimulationMode={health.simulationMode}
      backendVersion={health.version}
      onStart={consultation.startConsultation}
      isStarting={consultation.isStarting}
    />
  );
}