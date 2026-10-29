/** Explicit route context: a selected run is meaningful only within its project. */
export const DEMO_PROJECT_ID = "proj_1";
export const DEMO_RUN_ID = "run_42";
export type RunContext = { projectId: string; runId: string };
export type ProjectDestination = "arena" | "council" | "history" | "compare" | "experiments" | "resources";

export function selectedRunId(projectId: string, requestedRunId: string | null) {
  return requestedRunId?.trim() || (projectId === DEMO_PROJECT_ID ? DEMO_RUN_ID : null);
}

export function projectHref(projectId: string, destination: ProjectDestination, context?: RunContext | null) {
  if (destination === "compare") return "/compare";
  if (destination === "resources") return "/resources";
  const suffix = { arena: "", council: "/council", history: "/history", experiments: "/kit" }[destination];
  const path = `/project/${encodeURIComponent(projectId)}${suffix}`;
  if (destination === "history" || context?.projectId !== projectId || !context.runId.trim()) return path;
  return `${path}?${new URLSearchParams({ run: context.runId })}`;
}
