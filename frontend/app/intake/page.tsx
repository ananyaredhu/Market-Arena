"use client";
// OWNER: Person C. Screen 2 mockup: "Idea Intake + Packs". Text is placeholder (lib/mock/intake.ts).
import { useEffect, useState } from "react";

import IdeaInput from "@/components/intake/IdeaInput";
import MissingAssumptions from "@/components/intake/MissingAssumptions";
import PackPicker from "@/components/intake/PackPicker";
import ProfileCard from "@/components/intake/ProfileCard";
import StepPills from "@/components/intake/StepPills";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { post } from "@/lib/api";
import { IDEA_TEXT, INTAKE_STEPS, MISSING_ASSUMPTIONS, PACKS } from "@/lib/mock/intake";
import type { ProductProfile } from "@/lib/types";

export default function IntakePage() {
  const [profile, setProfile] = useState<ProductProfile | null>(null);
  const [pack, setPack] = useState("saas");

  useEffect(() => {
    post<{ profile: ProductProfile }>("/projects").then((r) => setProfile(r.profile));
  }, []);

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
          <IdeaInput initial={IDEA_TEXT} />
          <MissingAssumptions items={MISSING_ASSUMPTIONS} />
        </section>
        <section className="flex min-w-0 flex-[1_1_400px] flex-col">
          {profile ? <ProfileCard profile={profile} /> : <p className="text-muted">Loading…</p>}
        </section>
      </div>

      <PackPicker packs={PACKS} value={pack} onChange={setPack} />
    </PageShell>
  );
}
