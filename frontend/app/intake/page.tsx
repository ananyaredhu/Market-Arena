"use client";
// OWNER: Person C. Screen 2: submit a real idea and show the extracted profile.
import { useState } from "react";

import IdeaInput from "@/components/intake/IdeaInput";
import MissingAssumptions from "@/components/intake/MissingAssumptions";
import PackPicker from "@/components/intake/PackPicker";
import ProfileCard from "@/components/intake/ProfileCard";
import StepPills from "@/components/intake/StepPills";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { post } from "@/lib/api";
import { IDEA_TEXT, INTAKE_STEPS, PACKS } from "@/lib/mock/intake";
import type { ProductProfile } from "@/lib/types";

const AVAILABLE_PACKS = PACKS.filter((option) => option.id === "saas" || option.id === "cafe");

export default function IntakePage() {
  const [profile, setProfile] = useState<ProductProfile | null>(null);
  const [pack, setPack] = useState("saas");
  const [projectId, setProjectId] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitIdea(idea: string) {
    if (!idea.trim()) {
      setValidationError("Enter a product idea before building your market.");
      setRequestError(null);
      return;
    }
    setValidationError(null);
    setRequestError(null);
    setIsSubmitting(true);
    try {
      const result = await post<{ id: string; profile: ProductProfile }>("/projects", { idea, pack });
      setProjectId(result.id);
      setProfile(result.profile);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "We could not build your market. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <PageShell glow="intake" className="!gap-7">
      <AppHeader disclaimer={false} right={<StepPills steps={INTAKE_STEPS} current={0} />} />

      <div>
        <h1 className="m-0 max-w-[760px] font-display text-5xl font-bold leading-[1.05] tracking-[-0.02em]">
          Tell us the idea. <span className="text-accent">We’ll build the market.</span>
        </h1>
        <p className="mt-3 max-w-[640px] text-[17px] leading-normal text-muted">
          Paste a paragraph or fill the form. Market Arena extracts the product, flags what you haven’t decided yet, and
          picks the right industry pack.
        </p>
      </div>

      <div className="flex flex-wrap items-stretch gap-6">
        <section className="flex min-w-0 flex-[1_1_520px] flex-col gap-3">
          <IdeaInput initial={IDEA_TEXT} disabled={isSubmitting} onSubmit={submitIdea} />
          {validationError && <p role="alert" className="m-0 text-sm text-warn-ink">{validationError}</p>}
          {requestError && <p role="alert" className="m-0 text-sm text-warn-ink">{requestError}</p>}
          {profile && <MissingAssumptions items={profile.missing_assumptions.map((question) => ({ question }))} />}
        </section>
        <section className="flex min-w-0 flex-[1_1_400px] flex-col">
          {profile ? <ProfileCard profile={profile} /> : <p className="text-muted">Build your market to see the extracted profile.</p>}
          {projectId && <p className="mt-2 font-mono text-xs text-muted">Project {projectId}</p>}
        </section>
      </div>

      <PackPicker packs={AVAILABLE_PACKS} value={pack} onChange={setPack} />
    </PageShell>
  );
}
