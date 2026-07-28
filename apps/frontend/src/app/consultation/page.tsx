"use client";

import { useConsultation } from "@/hooks/use-consultation";
import { useHealthCheck } from "@/hooks/use-health-check";
import { ConsultationFeature } from "@/features/consultation/components/consultation-feature";

export default function ConsultationPage() {
  const consultation = useConsultation();
  const { health, isConnected } = useHealthCheck();

  return (
    <ConsultationFeature
      consultation={consultation}
      health={health}
      isConnected={isConnected}
    />
  );
}