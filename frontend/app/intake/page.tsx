"use client";
// OWNER: Person C. Screen 2: submit a real idea and show the extracted profile.
import { useRouter } from "next/navigation";
import { useState } from "react";

import IdeaInput from "@/components/intake/IdeaInput";
import MissingAssumptions from "@/components/intake/MissingAssumptions";
import PackPicker from "@/components/intake/PackPicker";
import ProfileCard from "@/components/intake/ProfileCard";
import StepPills from "@/components/intake/StepPills";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { createProject, createScenario, runScenario } from "@/lib/api";
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
  const [isRunning, setIsRunning] = useState(false);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const router = useRouter();

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
      const result = await createProject(idea, pack);
      setProjectId(result.id);
      setProfile(result.profile);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "We could not build your market. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function startSimulation() {
    if (!projectId || isRunning) return;
    setRequestError(null);
    setIsRunning(true);
    try {
      setRunStatus("Creating your market scenario…");
      const scenario = await createScenario(projectId);
      if (scenario.project_id !== projectId) {
        throw new Error("The scenario was created for a different project. Please try again.");
      }
      setRunStatus("Running the simulation…");
      const run = await runScenario(scenario.id);
      if (run.project_id !== projectId || run.scenario_id !== scenario.id) {
        throw new Error("The simulation returned mismatched project data. Please try again.");
      }
      setRunStatus("Simulation complete. Opening the Arena…");
      router.push(`/project/${encodeURIComponent(projectId)}?run=${encodeURIComponent(run.run_id)}`);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "The simulation could not be started.");
      setRunStatus(null);
    } finally {
      setIsRunning(false);
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
          {projectId && (
            <div className="mt-3 flex flex-col gap-2">
              <p className="m-0 font-mono text-xs text-muted">Project {projectId}</p>
              <button
                type="button"
                onClick={startSimulation}
                disabled={isRunning}
                className="min-h-11 rounded-[10px] bg-accent px-[18px] text-sm font-bold text-bg disabled:cursor-wait disabled:opacity-60"
              >
                {isRunning ? "Starting simulation…" : "Start simulation →"}
              </button>
              {runStatus && <p className="m-0 text-sm text-muted" role="status">{runStatus}</p>}
            </div>
          )}
        </section>
      </div>

      <PackPicker packs={AVAILABLE_PACKS} value={pack} onChange={setPack} />
    </PageShell>
  );
}
