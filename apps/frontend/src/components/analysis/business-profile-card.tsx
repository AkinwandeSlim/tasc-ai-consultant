"use client";

import type { BusinessProfileDTO } from "@/types/api";
import {
  Building2,
  Users,
  ListChecks,
  Wrench,
  Goal,
  Calendar,
  Banknote,
  UserCheck,
  Cpu,
} from "lucide-react";

interface BusinessProfileCardProps {
  profile: BusinessProfileDTO;
}

export function BusinessProfileCard({ profile }: BusinessProfileCardProps) {
  const hasData =
    profile.industry ||
    profile.company_size ||
    profile.pain_points.length > 0 ||
    profile.current_tools.length > 0 ||
    profile.goals.length > 0 ||
    profile.timeline ||
    profile.budget_band ||
    profile.decision_authority;

  if (!hasData) {
    return (
      <div className="rounded-lg border border-border p-3">
        <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
          Business Profile
        </p>
        <p className="text-body-sm text-muted-foreground">
          Not identified yet
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
        Business Profile
      </p>
      <div className="space-y-2">
        {profile.industry && (
          <div className="flex items-center gap-2 text-body-sm">
            <Building2 className="size-3.5 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Industry:</span>
            <span className="font-medium capitalize">{profile.industry}</span>
          </div>
        )}
        {profile.company_size && (
          <div className="flex items-center gap-2 text-body-sm">
            <Users className="size-3.5 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Size:</span>
            <span className="font-medium">{profile.company_size}</span>
          </div>
        )}
        {profile.goals.length > 0 && (
          <div className="flex items-start gap-2 text-body-sm">
            <Goal className="size-3.5 text-muted-foreground shrink-0 mt-0.5" />
            <span className="text-muted-foreground shrink-0">Goals:</span>
            <span>{profile.goals.join(", ")}</span>
          </div>
        )}
        {profile.pain_points.length > 0 && (
          <div className="flex items-start gap-2 text-body-sm">
            <ListChecks className="size-3.5 text-muted-foreground shrink-0 mt-0.5" />
            <span className="text-muted-foreground shrink-0">Pain:</span>
            <span>
              {profile.pain_points.map((p) => p.label).join("; ")}
            </span>
          </div>
        )}
        {profile.current_tools.length > 0 && (
          <div className="flex items-start gap-2 text-body-sm">
            <Wrench className="size-3.5 text-muted-foreground shrink-0 mt-0.5" />
            <span className="text-muted-foreground shrink-0">Tools:</span>
            <span>{profile.current_tools.join(", ")}</span>
          </div>
        )}
        {profile.timeline && (
          <div className="flex items-center gap-2 text-body-sm">
            <Calendar className="size-3.5 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Timeline:</span>
            <span className="font-medium capitalize">
              {profile.timeline.replace(/_/g, " ")}
            </span>
          </div>
        )}
        {profile.budget_band && (
          <div className="flex items-center gap-2 text-body-sm">
            <Banknote className="size-3.5 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Budget:</span>
            <span className="font-medium capitalize">
              {profile.budget_band.replace(/_/g, " ")}
            </span>
          </div>
        )}
        {profile.decision_authority && (
          <div className="flex items-center gap-2 text-body-sm">
            <UserCheck className="size-3.5 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Authority:</span>
            <span className="font-medium capitalize">
              {profile.decision_authority.replace(/_/g, " ")}
            </span>
          </div>
        )}
        {profile.core_slots_filled > 0 && (
          <div className="flex items-center gap-2 text-body-sm">
            <Cpu className="size-3.5 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">AI Readiness:</span>
            <span className="font-medium">
              {profile.total_slots_filled}/9 details captured
            </span>
          </div>
        )}
      </div>
    </div>
  );
}