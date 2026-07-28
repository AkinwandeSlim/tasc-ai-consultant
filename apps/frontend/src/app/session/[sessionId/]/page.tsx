"use client";

import { useParams } from "next/navigation";
import { ConsultationFeature } from "@/features/consultation/components/consultation-feature";

export default function SessionPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;

  return <ConsultationFeature sessionId={sessionId} />;
}
