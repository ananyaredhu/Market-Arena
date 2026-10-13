// MOCK COPY for the intake screen (design placeholder text). Replace with real data from POST /projects.

export const IDEA_TEXT =
  "StudyFlow is a study planner for university students. It builds a weekly revision schedule from exam dates and re-plans when you fall behind. 14-day free trial, then S$9 a month.";

export const MISSING_ASSUMPTIONS = [
  { question: "Who are the closest rivals?", hint: "We’ll suggest three." },
  { question: "Is there a free tier?", hint: "Students compare against free tools." },
  { question: "Does it integrate with calendars?", hint: "Affects switching cost." },
];

export const INTAKE_STEPS = ["Idea", "Rivals", "Population", "Run"];

export interface PackOption {
  id: string;
  name: string;
  blurb: string;
  tag: string;
  state: "selected" | "available" | "custom";
}

export const PACKS: PackOption[] = [
  { id: "saas", name: "Software / SaaS", tag: "Selected", state: "selected", blurb: "Free-tier alternatives, trial behaviour, switching cost, integrations." },
  { id: "cafe", name: "Café & local retail", tag: "MVP", state: "available", blurb: "Distance, wait time, footfall, repeat visits." },
  { id: "services", name: "Local services", tag: "MVP-lite", state: "available", blurb: "Trust, referrals, appointment friction." },
  { id: "custom", name: "Custom pack", tag: "Lower reliability", state: "custom", blurb: "Five questions build one on the fly." },
];

export const FEATURE_LABELS: Record<string, string> = {
  ai_planning: "AI planning",
  simplicity: "Simplicity",
  privacy: "Privacy",
  integrations: "Integrations",
};
