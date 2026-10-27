import { createScenario, runScenario, type RunStartResponse, type ScenarioResponse } from "./api";
import { projectHref } from "./run-context";

const ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,100}$/;
function validId(value: unknown): value is string { return typeof value === "string" && ID.test(value); }
function object(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null; }

export function assertScenarioForProject(value: unknown, projectId: string): asserts value is ScenarioResponse {
  if (!validId(projectId) || !object(value) || !validId(value.id) || value.project_id !== projectId) {
    throw new Error("The scenario returned missing or mismatched project data. Please try again.");
  }
}

export function assertRunForScenario(value: unknown, projectId: string, scenarioId: string): asserts value is RunStartResponse {
  if (!validId(projectId) || !validId(scenarioId) || !object(value) || !validId(value.run_id) ||
      value.project_id !== projectId || value.scenario_id !== scenarioId || value.status !== "done") {
    throw new Error("The simulation returned missing, incomplete or mismatched project data. Please try again.");
  }
}

/** Identical validation for fixture and real responses; no client-side mock fallback. */
export async function startProjectSimulation(projectId: string, progress: (message: string) => void = () => {}) {
  progress("Creating your market scenario…");
  const scenario = await createScenario(projectId);
  assertScenarioForProject(scenario, projectId);
  progress("Running the simulation…");
  const run = await runScenario(scenario.id);
  assertRunForScenario(run, projectId, scenario.id);
  return { run, href: projectHref(projectId, "arena", { projectId, runId: run.run_id }) };
}
